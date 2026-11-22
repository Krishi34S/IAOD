from app import create_app

app = create_app()
with app.test_client() as c:
    print('Unauth dashboard:', c.get('/api/dashboard/summary').status_code)
