from playwright.sync_api import sync_playwright
import os
import sys
sys.path.append("/app")

def test_frontend(page):
    page.goto("http://localhost:5000/")

    # Wait for the page to load
    page.wait_for_selector("body")

    # Take a screenshot of the main page
    page.screenshot(path="/app/verification/main_page.png", full_page=True)

    # Click on the edit button of the first case if it exists, otherwise just take main page
    edit_buttons = page.locator(".btn-outline-info[title='Düzenle']")
    if edit_buttons.count() > 0:
        edit_buttons.first.click(force=True)
        try:
            page.wait_for_selector("#editCaseModal", state="visible", timeout=5000)
            page.screenshot(path="/app/verification/edit_modal.png")
        except Exception as e:
            print("Modal wait timeout:", e)

if __name__ == "__main__":
    # Start the flask app in the background first if it isn't running
    import subprocess
    import time

    # Setup test DB
    os.environ['DATABASE_URL'] = 'sqlite:///test.db'

    # Initialize DB
    import app as flask_app
    with flask_app.app.app_context():
        flask_app.db.create_all()
        # Create a test case
        c = flask_app.Case(case_no="123", client="Test Client", city="Ankara", district="Merkez", court_office="Adliye", case_type="Ceza Davası", status="Aktif", priority="Acil")
        flask_app.db.session.add(c)
        flask_app.db.session.commit()

    server = subprocess.Popen(["flask", "run", "--host=0.0.0.0", "--port=5000"], env=os.environ.copy())
    time.sleep(3) # Wait for server to start

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            test_frontend(page)
            browser.close()
    finally:
        server.terminate()
