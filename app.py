import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from database import init_db, db
from models import EmailCampaign, Recipient, CampaignRecipient
from services.ai_service import generate_email, ai_refine_email, test_ai_connection, FALLBACK_MODELS
from services.email_service import send_email_campaign

load_dotenv()

app = Flask(__name__)
init_db(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/stats', methods=['GET'])
def get_stats():
    emails_sent = CampaignRecipient.query.filter_by(status='Sent').count()
    ai_drafts = EmailCampaign.query.count()
    recipients_count = Recipient.query.count()
    failed_emails = CampaignRecipient.query.filter_by(status='Failed').count()
    
    recent_campaigns = EmailCampaign.query.order_by(EmailCampaign.created_at.desc()).limit(5).all()
    recent_activity = [c.to_dict() for c in recent_campaigns]

    return jsonify({
        'emails_sent': emails_sent,
        'ai_drafts': ai_drafts,
        'recipients': recipients_count,
        'failed_emails': failed_emails,
        'recent_activity': recent_activity
    })

@app.route('/api/generate', methods=['POST'])
def generate():
    data = request.get_json(silent=True) or {}
    subject = data.get('subject', '').strip()
    tone = data.get('tone', 'Professional')
    instructions = data.get('instructions', '').strip()
    model = data.get('model')

    if not subject:
        return jsonify({'error': 'Subject or topic is required'}), 400

    try:
        result = generate_email(subject=subject, tone=tone, additional_instructions=instructions, model=model)
        return jsonify({
            'subject': subject,
            'content': result['content'],
            'tone': tone,
            'model_used': result.get('model_used', 'Gemini')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/refine', methods=['POST'])
def refine():
    data = request.get_json(silent=True) or {}
    content = data.get('content', '').strip()
    instruction = data.get('instruction', '').strip()
    tone = data.get('tone', 'Professional')
    model = data.get('model')

    if not content:
        return jsonify({'error': 'Email content is required to refine'}), 400
    if not instruction:
        return jsonify({'error': 'Instruction is required'}), 400

    try:
        result = ai_refine_email(content=content, instruction=instruction, tone=tone, model=model)
        return jsonify({
            'content': result['content'],
            'model_used': result.get('model_used', 'Gemini')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/test-ai', methods=['POST', 'GET'])
def test_ai():
    data = request.get_json(silent=True) or {}
    api_key = data.get('api_key')
    model = data.get('model')
    res = test_ai_connection(api_key=api_key, model=model)
    return jsonify(res)

@app.route('/api/campaigns', methods=['POST'])
def create_campaign():
    data = request.get_json(silent=True) or {}
    subject = data.get('subject', '').strip()
    content = data.get('content', '').strip()
    tone = data.get('tone', 'Professional')

    if not subject or not content:
        return jsonify({'error': 'Subject and content are required'}), 400

    campaign = EmailCampaign(
        subject=subject,
        content=content,
        tone=tone,
        status='Draft'
    )
    db.session.add(campaign)
    db.session.commit()
    return jsonify({'id': campaign.id, 'message': 'Draft saved successfully'})

@app.route('/api/campaigns/<int:campaign_id>', methods=['GET'])
def get_campaign(campaign_id):
    campaign = EmailCampaign.query.get_or_404(campaign_id)
    return jsonify(campaign.to_dict())

@app.route('/api/campaigns/<int:campaign_id>', methods=['DELETE'])
def delete_campaign(campaign_id):
    campaign = EmailCampaign.query.get_or_404(campaign_id)
    CampaignRecipient.query.filter_by(campaign_id=campaign.id).delete()
    db.session.delete(campaign)
    db.session.commit()
    return jsonify({'message': 'Campaign deleted successfully'})

@app.route('/api/send', methods=['POST'])
def send_emails():
    data = request.get_json(silent=True) or {}
    subject = data.get('subject', '').strip()
    content = data.get('content', '').strip()
    recipient_emails = data.get('recipients', [])

    if not subject or not content or not recipient_emails:
        return jsonify({'error': 'Subject, content, and recipients are required'}), 400

    campaign = EmailCampaign(
        subject=subject,
        content=content,
        status='Sending'
    )
    db.session.add(campaign)
    db.session.commit()

    # Add recipients to DB if they don't exist
    for email in recipient_emails:
        recipient = Recipient.query.filter_by(email=email).first()
        if not recipient:
            recipient = Recipient(email=email)
            db.session.add(recipient)
        
        cr = CampaignRecipient(campaign_id=campaign.id, recipient_email=email)
        db.session.add(cr)
    
    db.session.commit()

    # Send emails via SMTP
    send_result = send_email_campaign(subject, content, recipient_emails)
    
    if send_result.get('success'):
        campaign.status = 'Sent'
        campaign.sent_at = datetime.utcnow()
        
        # Update individual statuses
        for res in send_result.get('results', []):
            cr = CampaignRecipient.query.filter_by(campaign_id=campaign.id, recipient_email=res['email']).first()
            if cr:
                cr.status = res['status']
            if res['status'] == 'Sent':
                rec = Recipient.query.filter_by(email=res['email']).first()
                if rec:
                    rec.emails_sent += 1
                    rec.last_contact = datetime.utcnow()
        
        # Check for partial success
        failed_count = sum(1 for r in send_result.get('results', []) if r.get('status') == 'Failed')
        if failed_count > 0 and failed_count < len(recipient_emails):
            campaign.status = 'Partial'
        elif failed_count == len(recipient_emails):
            campaign.status = 'Failed'
            
    else:
        campaign.status = 'Failed'
        for cr in CampaignRecipient.query.filter_by(campaign_id=campaign.id).all():
            cr.status = 'Failed'

    db.session.commit()

    return jsonify({
        'success': send_result.get('success', False),
        'campaign_id': campaign.id,
        'results': send_result.get('results', []),
        'error': send_result.get('error')
    })

@app.route('/api/history', methods=['GET'])
def get_history():
    campaigns = EmailCampaign.query.order_by(EmailCampaign.created_at.desc()).all()
    return jsonify([c.to_dict() for c in campaigns])

@app.route('/api/recipients', methods=['GET'])
def get_recipients():
    recipients = Recipient.query.order_by(Recipient.id.desc()).all()
    return jsonify([r.to_dict() for r in recipients])

@app.route('/api/recipients', methods=['POST'])
def add_recipient():
    data = request.get_json(silent=True) or {}
    email = data.get('email', '').strip().lower()
    name = data.get('name', '').strip()

    if not email:
        return jsonify({'error': 'Email is required'}), 400

    existing = Recipient.query.filter_by(email=email).first()
    if existing:
        return jsonify({'error': 'Recipient already exists', 'recipient': existing.to_dict()}), 409

    recipient = Recipient(email=email, name=name if name else None)
    db.session.add(recipient)
    db.session.commit()
    return jsonify({'message': 'Recipient added successfully', 'recipient': recipient.to_dict()}), 201

@app.route('/api/recipients/<int:recipient_id>', methods=['DELETE'])
def delete_recipient(recipient_id):
    recipient = Recipient.query.get_or_404(recipient_id)
    db.session.delete(recipient)
    db.session.commit()
    return jsonify({'message': 'Recipient deleted successfully'})

@app.route('/api/settings', methods=['GET'])
def get_settings():
    smtp_email = os.environ.get('SMTP_EMAIL') or os.environ.get('GMAIL_SENDER_EMAIL', '')
    smtp_pass = os.environ.get('SMTP_PASSWORD') or os.environ.get('GMAIL_APP_PASSWORD', '')
    gemini_key = os.environ.get('GEMINI_API_KEY', '')
    current_model = os.environ.get('GEMINI_MODEL', 'gemini-3.5-flash')

    is_smtp_configured = bool(smtp_email and smtp_pass and smtp_email != 'your_email@gmail.com')
    is_api_configured = bool(gemini_key and gemini_key != 'your_gemini_api_key_here')

    return jsonify({
        'email': smtp_email if is_smtp_configured else 'Not configured',
        'smtp_connected': is_smtp_configured,
        'api_connected': is_api_configured,
        'current_model': current_model,
        'available_models': FALLBACK_MODELS
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 1212))
    debug = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 't')
    print(f"Starting MailPilot on http://127.0.0.1:{port} (debug={debug})")
    app.run(debug=debug, port=port)
