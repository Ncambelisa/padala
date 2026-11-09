"""Local administration. Never seeds demo users automatically."""
from __future__ import annotations
import argparse
import getpass
from datetime import date, timedelta
from sqlalchemy import select, delete
from .config import Settings
from .migrations import upgrade_database
from .db import Base, make_database
from .models import *
from .security import HASHER

DEMO_PASSWORD='PadalaDemo!2026'

def main():
    parser=argparse.ArgumentParser(description='Padala local administration')
    parser.add_argument('command',choices=['init','seed','reset-password','purge-unused-uploads','check-production'])
    parser.add_argument('--email')
    args=parser.parse_args()
    settings=Settings()
    if args.command=='check-production':
        settings.validate()
        print('Configuration passes Padala\'s code-level production safety checks. External release gates still apply.')
        return
    engine,factory=make_database(settings);upgrade_database(engine)
    with factory() as db:
        if args.command=='init':
            print('Database initialized. Create your household at the web sign-up screen.')
        elif args.command=='seed':
            if db.scalar(select(User).where(User.email=='anna@padala.test')):
                print('Demo household already exists; no records changed.');return
            household=Household(name='Santos family');db.add(household);db.flush()
            sender=User(household_id=household.id,name='Anna Santos',email='anna@padala.test',role='sender',password_hash=HASHER.hash(DEMO_PASSWORD))
            family=User(household_id=household.id,name='Miguel Santos',email='miguel@padala.test',role='member',password_hash=HASHER.hash(DEMO_PASSWORD))
            db.add_all([sender,family]);db.flush()
            today=date.today()
            r=Remittance(household_id=household.id,title='November household support',amount_minor=3000000,received_on=today.isoformat(),recipient_id=family.id,source_currency='AED',source_amount='2000',confirmed=True)
            db.add(r);db.flush()
            allocations=[]
            for name,amount,kind in [('Rent',1000000,'expense'),('Groceries',700000,'expense'),('School',500000,'expense'),('Utilities',300000,'expense'),('Savings',500000,'savings')]:
                a=Allocation(remittance_id=r.id,name=name,kind=kind,amount_minor=amount,assigned_to=family.id,due_on=(today+timedelta(days=7)).isoformat())
                allocations.append(a);db.add(a)
            db.flush()
            for index,amount,merchant,status in [(0,1000000,'Rent acknowledgment','accepted'),(1,285000,'Weekly groceries','pending'),(4,500000,'Savings deposit record','pending')]:
                # Deliberately declared without images; no fabricated bank confirmations.
                e=Evidence(household_id=household.id,remittance_id=r.id,uploader_id=family.id,merchant=merchant,amount_minor=amount,occurred_on=today.isoformat(),note='Fictional demonstration record. No real receipt or bank confirmation.',status=status,checks=[])
                db.add(e);db.flush();db.add(EvidenceLine(evidence_id=e.id,allocation_id=allocations[index].id,amount_minor=amount))
            db.add(AuditEvent(household_id=household.id,actor='Demo setup',action='demo_seeded',detail='Fictional household created. All seed evidence is declared, not independently verified.',remittance_id=r.id))
            db.add(Notification(user_id=sender.id,title='Two records need your review',detail='Open the fictional November padala to try the review workflow.',remittance_id=r.id))
            db.commit()
            print('Created FICTIONAL demo household. Do not expose demo accounts publicly.')
            print('OFW: anna@padala.test | Family: miguel@padala.test')
            print('Password for both: '+DEMO_PASSWORD)
        elif args.command=='reset-password':
            email=args.email or input('Account email: ').strip().lower()
            user=db.scalar(select(User).where(User.email==email))
            if not user:
                raise SystemExit('Account not found.')
            password=getpass.getpass('New password (12-128 characters): ')
            if not 12<=len(password)<=128 or password!=getpass.getpass('Repeat password: '):
                raise SystemExit('Password invalid or confirmation does not match.')
            user.password_hash=HASHER.hash(password)
            db.execute(delete(LoginSession).where(LoginSession.user_id==user.id));db.commit()
            print('Password changed and sessions revoked.')
        else:
            referenced=select(Evidence.upload_id).where(Evidence.upload_id.is_not(None))
            rows=db.scalars(select(Upload).where(Upload.created_at<timestamp()-86400,Upload.id.not_in(referenced))).all()
            for row in rows:
                (settings.uploads_dir/row.storage_name).unlink(missing_ok=True);db.delete(row)
            db.commit();print(f'Removed {len(rows)} unsubmitted uploads older than 24 hours.')
    engine.dispose()

if __name__=='__main__':
    main()
