from playwright.sync_api import sync_playwright, expect

def verify_frontend():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Dashboard page
        page.goto("http://localhost:5000/")
        expect(page).to_have_title("ERATA HUKUK - Şehir Dışı Dosya Takip")

        # Check that the table exists
        expect(page.locator("table.table")).to_be_visible()

        # Check for our added dropdown options like Denizli and Malatya
        # The filter form's city select:
        city_select = page.locator("form.d-flex select[name='city']")
        expect(city_select).to_be_visible()

        # Click the 'Yeni Dosya' button to open the modal
        add_btn = page.get_by_role("button", name="Yeni Dosya")
        add_btn.click()
        expect(page.locator("#addCaseModal")).to_be_visible()

        # Add a test case to the table
        page.locator("#addCaseModal input[name='case_no']").fill("2024/TEST")
        page.locator("#addCaseModal input[name='client']").fill("Test User")
        page.locator("#addCaseModal select[name='city']").select_option("Denizli")
        page.locator("#addCaseModal button[type='submit']").click()

        # wait for page reload
        page.wait_for_load_state("networkidle")

        # Now click edit on the newly added item
        edit_btn = page.locator(".edit-btn").first
        expect(edit_btn).to_be_visible()
        edit_btn.click()

        expect(page.locator("#editCaseModal")).to_be_visible()

        # Try to open the edit modal (we have no cases but let's test the UI)
        page.goto("http://localhost:5000/rota")

        # Take a screenshot
        page.screenshot(path="verification.png")

        browser.close()

if __name__ == "__main__":
    verify_frontend()
