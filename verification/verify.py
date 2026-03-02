from playwright.sync_api import sync_playwright

def verify():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Verify index page
        page.goto("http://localhost:5000")
        page.wait_for_timeout(2000)
        page.screenshot(path="/home/jules/verification/dashboard.png")

        # Verify route page
        page.goto("http://localhost:5000/rota")
        page.wait_for_timeout(2000)
        page.screenshot(path="/home/jules/verification/route.png")

        browser.close()

if __name__ == "__main__":
    verify()
