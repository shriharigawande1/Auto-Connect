# AutoConnect — Full Working MVP

A complete local-service platform based on the supplied AutoConnect flow.

## Included
- User registration/login
- Worker registration/login
- Admin login + worker verification
- Smart problem analysis (demo rule-based AI endpoint)
- Worker search/filter
- Worker profile
- Booking + status lifecycle
- Worker dashboard + availability
- User dashboard + booking history
- Chat per booking
- Notifications
- Favourite workers
- Emergency worker finder
- Demo QR payment
- Payment confirmation
- Feedback + rating
- Digital receipt

## Demo accounts
User: user@autoconnect.demo / 123456
Worker: rahul@autoconnect.demo / 123456
Admin: admin@autoconnect.demo / admin123

## Windows setup
1. Install Python 3.10+.
2. Open CMD in this folder.
3. Run:
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   python app.py
4. Open http://127.0.0.1:5000

The database `autoconnect.db` is created automatically.

## Important demo notes
DigiLocker, real UPI payment confirmation, real GPS/maps, production AI vision and OTP/SMS are represented by working demo flows. Real integrations need their official APIs/credentials and authorization.
