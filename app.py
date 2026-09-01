import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from database import init_db, db
from models import EmailCampaign, Recipient, CampaignRecipient

from services.ai_service import (
    generate_email,
    ai_refine_email,
    test_ai_connection,
    FALLBACK_MODELS
)

from services.email_service import send_email_campaign


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv(override=True)


# ============================================================
# FLASK APPLICATION
# ============================================================

app = Flask(__name__)

init_db(app)


# ============================================================
# HOME
# ============================================================

@app.route('/')
def index():
    return render_template('index.html')


# ============================================================
# DASHBOARD STATISTICS
# ============================================================

@app.route('/api/stats', methods=['GET'])
def get_stats():

    emails_sent = CampaignRecipient.query.filter_by(
        status='Sent'
    ).count()

    ai_drafts = EmailCampaign.query.count()

    recipients_count = Recipient.query.count()

    failed_emails = CampaignRecipient.query.filter_by(
        status='Failed'
    ).count()

    recent_campaigns = (
        EmailCampaign.query
        .order_by(EmailCampaign.created_at.desc())
        .limit(5)
        .all()
    )

    recent_activity = [
        campaign.to_dict()
        for campaign in recent_campaigns
    ]

    return jsonify({
        'emails_sent': emails_sent,
        'ai_drafts': ai_drafts,
        'recipients': recipients_count,
        'failed_emails': failed_emails,
        'recent_activity': recent_activity
    })


# ============================================================
# AI EMAIL GENERATION
# ============================================================

@app.route('/api/generate', methods=['POST'])
def generate():

    data = request.get_json(silent=True) or {}

    subject = str(data.get('subject', '')).strip()
    tone = str(data.get('tone', 'Professional')).strip()
    instructions = str(
        data.get('instructions', '')
    ).strip()

    model = data.get('model')
    api_key = data.get('api_key')

    if not subject:
        return jsonify({
            'error': 'Subject or topic is required'
        }), 400

    try:

        result = generate_email(
            subject=subject,
            tone=tone,
            additional_instructions=instructions,
            model=model,
            api_key=api_key
        )

        return jsonify({
            'success': True,
            'subject': subject,
            'content': result.get('content', ''),
            'tone': tone,
            'model_used': result.get(
                'model_used',
                'NVIDIA AI'
            )
        })

    except Exception as e:

        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================
# AI EMAIL REFINEMENT
# ============================================================

@app.route('/api/refine', methods=['POST'])
def refine():

    data = request.get_json(silent=True) or {}

    content = str(
        data.get('content', '')
    ).strip()

    instruction = str(
        data.get('instruction', '')
    ).strip()

    tone = str(
        data.get('tone', 'Professional')
    ).strip()

    model = data.get('model')
    api_key = data.get('api_key')

    if not content:
        return jsonify({
            'error': 'Email content is required to refine'
        }), 400

    if not instruction:
        return jsonify({
            'error': 'Instruction is required'
        }), 400

    try:

        result = ai_refine_email(
            content=content,
            instruction=instruction,
            tone=tone,
            model=model,
            api_key=api_key
        )

        return jsonify({
            'success': True,
            'content': result.get('content', ''),
            'model_used': result.get(
                'model_used',
                'NVIDIA AI'
            )
        })

    except Exception as e:

        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================
# TEST AI CONNECTION
# ============================================================

@app.route('/api/test-ai', methods=['POST', 'GET'])
def test_ai():

    data = request.get_json(silent=True) or {}

    api_key = data.get('api_key')
    model = data.get('model')

    try:

        result = test_ai_connection(
            api_key=api_key,
            model=model
        )

        return jsonify(result)

    except Exception as e:

        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================
# CREATE / SAVE CAMPAIGN
# ============================================================

@app.route('/api/campaigns', methods=['POST'])
def create_campaign():

    data = request.get_json(silent=True) or {}

    subject = str(
        data.get('subject', '')
    ).strip()

    content = str(
        data.get('content', '')
    ).strip()

    tone = str(
        data.get('tone', 'Professional')
    ).strip()

    if not subject or not content:
        return jsonify({
            'error': 'Subject and content are required'
        }), 400

    campaign = EmailCampaign(
        subject=subject,
        content=content,
        tone=tone,
        status='Draft'
    )

    db.session.add(campaign)
    db.session.commit()

    return jsonify({
        'success': True,
        'id': campaign.id,
        'message': 'Draft saved successfully'
    }), 201


# ============================================================
# GET SINGLE CAMPAIGN
# ============================================================

@app.route('/api/campaigns/<int:campaign_id>', methods=['GET'])
def get_campaign(campaign_id):

    campaign = EmailCampaign.query.get_or_404(
        campaign_id
    )

    return jsonify(
        campaign.to_dict()
    )


# ============================================================
# DELETE CAMPAIGN
# ============================================================

@app.route('/api/campaigns/<int:campaign_id>', methods=['DELETE'])
def delete_campaign(campaign_id):

    campaign = EmailCampaign.query.get_or_404(
        campaign_id
    )

    CampaignRecipient.query.filter_by(
        campaign_id=campaign.id
    ).delete()

    db.session.delete(campaign)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Campaign deleted successfully'
    })


# ============================================================
# SEND EMAIL CAMPAIGN
# ============================================================

@app.route('/api/send', methods=['POST'])
def send_emails():

    data = request.get_json(silent=True) or {}

    subject = str(
        data.get('subject', '')
    ).strip()

    content = str(
        data.get('content', '')
    ).strip()

    recipient_emails = data.get(
        'recipients',
        []
    )

    # --------------------------------------------------------
    # VALIDATE RECIPIENT LIST
    # --------------------------------------------------------

    if not isinstance(recipient_emails, list):
        return jsonify({
            'error': 'Recipients must be a list'
        }), 400

    # Clean and remove duplicate emails
    recipient_emails = list({
        str(email).strip().lower()
        for email in recipient_emails
        if str(email).strip()
    })

    if not subject:
        return jsonify({
            'error': 'Subject is required'
        }), 400

    if not content:
        return jsonify({
            'error': 'Email content is required'
        }), 400

    if not recipient_emails:
        return jsonify({
            'error': 'At least one recipient is required'
        }), 400

    # --------------------------------------------------------
    # CREATE CAMPAIGN
    # --------------------------------------------------------

    campaign = EmailCampaign(
        subject=subject,
        content=content,
        status='Sending'
    )

    db.session.add(campaign)
    db.session.commit()

    # --------------------------------------------------------
    # ADD RECIPIENTS
    # --------------------------------------------------------

    for email in recipient_emails:

        recipient = Recipient.query.filter_by(
            email=email
        ).first()

        if not recipient:

            recipient = Recipient(
                email=email
            )

            db.session.add(recipient)
            db.session.flush()

        campaign_recipient = CampaignRecipient(
            campaign_id=campaign.id,
            recipient_email=email,
            status='Pending'
        )

        db.session.add(
            campaign_recipient
        )

    db.session.commit()

    # --------------------------------------------------------
    # SEND EMAILS
    # --------------------------------------------------------

    try:

        send_result = send_email_campaign(
            subject,
            content,
            recipient_emails
        )

    except Exception as e:

        campaign.status = 'Failed'

        campaign_recipients = (
            CampaignRecipient.query
            .filter_by(campaign_id=campaign.id)
            .all()
        )

        for cr in campaign_recipients:
            cr.status = 'Failed'

        db.session.commit()

        return jsonify({
            'success': False,
            'campaign_id': campaign.id,
            'results': [],
            'error': str(e)
        }), 500

    # --------------------------------------------------------
    # PROCESS SEND RESULTS
    # --------------------------------------------------------

    results = send_result.get(
        'results',
        []
    )

    successful_count = 0
    failed_count = 0

    for result in results:

        email = str(
            result.get('email', '')
        ).strip().lower()

        status = result.get(
            'status',
            'Failed'
        )

        campaign_recipient = (
            CampaignRecipient.query
            .filter_by(
                campaign_id=campaign.id,
                recipient_email=email
            )
            .first()
        )

        if campaign_recipient:

            campaign_recipient.status = status

        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        if status == 'Sent':

            successful_count += 1

            recipient = Recipient.query.filter_by(
                email=email
            ).first()

            if recipient:

                recipient.emails_sent = (
                    recipient.emails_sent or 0
                ) + 1

                recipient.last_contact = datetime.utcnow()

        # ----------------------------------------------------
        # FAILED
        # ----------------------------------------------------

        else:

            failed_count += 1

    # --------------------------------------------------------
    # DETERMINE CAMPAIGN STATUS
    # --------------------------------------------------------

    total_recipients = len(
        recipient_emails
    )

    if successful_count == total_recipients:

        campaign.status = 'Sent'
        campaign.sent_at = datetime.utcnow()

    elif successful_count > 0:

        campaign.status = 'Partial'
        campaign.sent_at = datetime.utcnow()

    else:

        campaign.status = 'Failed'

    # If the email service itself reports total failure
    if not send_result.get('success', False):

        if successful_count == 0:
            campaign.status = 'Failed'

    db.session.commit()

    return jsonify({
        'success': send_result.get(
            'success',
            False
        ),
        'campaign_id': campaign.id,
        'status': campaign.status,
        'results': results,
        'error': send_result.get('error')
    })


# ============================================================
# CAMPAIGN HISTORY
# ============================================================

@app.route('/api/history', methods=['GET'])
def get_history():

    campaigns = (
        EmailCampaign.query
        .order_by(
            EmailCampaign.created_at.desc()
        )
        .all()
    )

    return jsonify([
        campaign.to_dict()
        for campaign in campaigns
    ])


# ============================================================
# GET RECIPIENTS
# ============================================================

@app.route('/api/recipients', methods=['GET'])
def get_recipients():

    recipients = (
        Recipient.query
        .order_by(
            Recipient.id.desc()
        )
        .all()
    )

    return jsonify([
        recipient.to_dict()
        for recipient in recipients
    ])


# ============================================================
# ADD RECIPIENT
# ============================================================

@app.route('/api/recipients', methods=['POST'])
def add_recipient():

    data = request.get_json(silent=True) or {}

    email = str(
        data.get('email', '')
    ).strip().lower()

    name = str(
        data.get('name', '')
    ).strip()

    if not email:
        return jsonify({
            'error': 'Email is required'
        }), 400

    existing = Recipient.query.filter_by(
        email=email
    ).first()

    if existing:

        return jsonify({
            'error': 'Recipient already exists',
            'recipient': existing.to_dict()
        }), 409

    recipient = Recipient(
        email=email,
        name=name if name else None
    )

    db.session.add(recipient)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Recipient added successfully',
        'recipient': recipient.to_dict()
    }), 201


# ============================================================
# DELETE RECIPIENT
# ============================================================

@app.route('/api/recipients/<int:recipient_id>', methods=['DELETE'])
def delete_recipient(recipient_id):

    recipient = Recipient.query.get_or_404(
        recipient_id
    )

    db.session.delete(recipient)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Recipient deleted successfully'
    })


# ============================================================
# APPLICATION SETTINGS
# ============================================================

@app.route('/api/settings', methods=['GET'])
def get_settings():

    # --------------------------------------------------------
    # SMTP CONFIGURATION
    # --------------------------------------------------------

    smtp_email = os.environ.get(
        'SMTP_EMAIL',
        ''
    ).strip()

    smtp_password = os.environ.get(
        'SMTP_PASSWORD',
        ''
    ).strip()

    smtp_server = os.environ.get(
        'SMTP_SERVER',
        'smtp.gmail.com'
    ).strip()

    smtp_port = int(
        os.environ.get(
            'SMTP_PORT',
            '587'
        )
    )

    smtp_sender_name = os.environ.get(
        'SMTP_SENDER_NAME',
        'MailPilot'
    ).strip()

    # --------------------------------------------------------
    # NVIDIA AI CONFIGURATION
    # --------------------------------------------------------

    nvidia_api_key = os.environ.get(
        'NVIDIA_API_KEY',
        ''
    ).strip()

    nvidia_model = os.environ.get(
        'NVIDIA_MODEL',
        ''
    ).strip()

    # --------------------------------------------------------
    # CONFIGURATION STATUS
    # --------------------------------------------------------

    is_smtp_configured = bool(
        smtp_email
        and smtp_password
        and smtp_email != 'your_email@gmail.com'
        and smtp_password != 'your_16_char_app_password_here'
    )

    is_ai_configured = bool(
        nvidia_api_key
        and nvidia_api_key != 'your_nvidia_api_key_here'
    )

    # --------------------------------------------------------
    # MODEL
    # --------------------------------------------------------

    current_model = (
        nvidia_model
        if nvidia_model
        else (
            FALLBACK_MODELS[0]
            if FALLBACK_MODELS
            else 'NVIDIA AI'
        )
    )

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return jsonify({
        'email': (
            smtp_email
            if is_smtp_configured
            else 'Not configured'
        ),

        'smtp_connected': is_smtp_configured,

        'smtp_server': smtp_server,

        'smtp_port': smtp_port,

        'sender_name': smtp_sender_name,

        'api_connected': is_ai_configured,

        'ai_provider': 'NVIDIA AI',

        'current_model': current_model,

        'available_models': FALLBACK_MODELS
    })


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == '__main__':

    port = int(
        os.environ.get(
            'PORT',
            '1212'
        )
    )

    debug = (
        os.environ.get(
            'DEBUG',
            'False'
        ).lower()
        in ('true', '1', 't', 'yes')
    )

    print(
        f"Starting MailPilot on "
        f"http://127.0.0.1:{port} "
        f"(debug={debug})"
    )

    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )
