from datetime import datetime
from database import db

class EmailCampaign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    tone = db.Column(db.String(50))
    status = db.Column(db.String(50), default='Draft') # Draft, Sending, Sent, Partial
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sent_at = db.Column(db.DateTime, nullable=True)

    recipients = db.relationship('CampaignRecipient', backref='campaign', lazy=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def to_dict(self):
        return {
            'id': self.id,
            'subject': self.subject,
            'content': self.content,
            'tone': self.tone,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'recipient_count': len(self.recipients)
        }

class Recipient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    emails_sent = db.Column(db.Integer, default=0)
    last_contact = db.Column(db.DateTime, nullable=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'emails_sent': self.emails_sent,
            'last_contact': self.last_contact.isoformat() if self.last_contact else None
        }

class CampaignRecipient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('email_campaign.id'), nullable=False)
    recipient_email = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(50), default='Pending') # Pending, Sent, Failed

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def to_dict(self):
        return {
            'id': self.id,
            'campaign_id': self.campaign_id,
            'recipient_email': self.recipient_email,
            'status': self.status
        }
