




from pathlib import Path
import random
import time
from playwright.sync_api import sync_playwright
# import tldextract
# from experiments.utils import resolve_paths,measure_time, resource_path


def auto_scroll(page):
    page.evaluate("""
        async () => {
            await new Promise(resolve => {
                let totalHeight = 0;
                const distance = 100;
                const timer = setInterval(() => {
                    window.scrollBy(0, distance);
                    totalHeight += distance;

                    if (totalHeight >= document.body.scrollHeight) {
                        clearInterval(timer);
                        resolve();
                    }
                }, 100);
            });
        }
    """)

def handle_cookie(page):
    # Remove cookie banners and overlays
    page.evaluate("""
        () => {
            const selectors = [
                '[id*="cookie"]',
                '[class*="cookie"]',
                '[id*="consent"]',
                '[class*="consent"]',
                '[class*="banner"]',
                '[class*="popup"]'
            ];
            selectors.forEach(sel => {
                document.querySelectorAll(sel).forEach(el => el.remove());
            });
        }
    """)



# @measure_time
# @resolve_paths("path")
def take_playwright_fullpage(url, path="fullpage_playwright.png"):

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")


        # ⬇️ Auto-scroll to trigger lazy loading (pagination)
        auto_scroll(page)

        # ⏳ Optional wait for extra lazy elements to appear
        time.sleep(1)

        handle_cookie(page)


        # 🖼️ Now take full screenshot
        page.screenshot(path=path, full_page=True)
        browser.close()

    print(f"✅ Saved full screenshot to {path}")








def auto_scroll_until_end(page, scroll_pause=0.5, max_idle_time=5):
    """
    Scrolls until no new content appears for `max_idle_time` seconds.
    """
    last_height = page.evaluate("document.body.scrollHeight")
    idle_time = 0
    start_time = time.time()

    while idle_time < max_idle_time:
        page.evaluate("window.scrollBy(0, window.innerHeight);")
        time.sleep(scroll_pause)

        new_height = page.evaluate("document.body.scrollHeight")
        if new_height == last_height:
            idle_time += scroll_pause
        else:
            idle_time = 0
            last_height = new_height

    print(f"✅ Scrolling finished in {round(time.time() - start_time, 2)}s")


import time

def auto_scroll_fixed(page, scroll_pause=1, max_loads=5):
    """
    Scrolls down until new content loads `max_loads` times.
    """
    last_height = page.evaluate("document.body.scrollHeight")
    loads = 0
    start_time = time.time()

    while loads < max_loads:
        page.evaluate("window.scrollBy(0, window.innerHeight);")
        page.wait_for_timeout(30000)
        time.sleep(scroll_pause)

        new_height = page.evaluate("document.body.scrollHeight")
        if new_height > last_height:
            loads += 1
            last_height = new_height
            print(f"📜 New content load #{loads}")
        else:
            # Give it a little extra chance if no height change
            time.sleep(scroll_pause)

    print(f"✅ Scrolling finished after {loads} loads in {round(time.time() - start_time, 2)}s")


def auto_scroll_n_times(page, n, scroll_pause=0.5):
    """
    Scrolls the page `n` times with a pause between each scroll.
    """
    start_time = time.time()

    for _ in range(n):
        page.evaluate("window.scrollBy(0, window.innerHeight);")
        time.sleep(scroll_pause)

    print(f"✅ Scrolled {n} times in {round(time.time() - start_time, 2)}s")
 

# @measure_time
def auto_scroll_and_wait(page, n, scroll_pause=0.5, max_wait_time=5):
    """
    Scrolls the page `n` times and waits for new content to load.
    """

    for _ in range(n):
        print(f"time : {_}")
        page.evaluate("window.scrollBy(0, window.innerHeight);")  # Scroll down
        time.sleep(scroll_pause)  # Pause for content to load
        end_time = time.time()
        wait_time = 0

        # Wait for new content to load or until max_wait_time is reached
        while wait_time < max_wait_time:
            new_height = page.evaluate("document.body.scrollHeight")  # Get the new height
            time.sleep(scroll_pause)  # Wait before checking again
            wait_time += scroll_pause

            if new_height > last_height:
                print("New content loaded.")
                last_height = new_height  # Update height if new content is loaded
                break  # Exit the waiting loop if new content loaded



# def click_pagination_until_end_multiple_same_selectors(page, selector, delay=2000):
#     """
#     Clicks ALL matching selectors until none remain visible.
#     """
#     while True:
#         buttons = page.query_selector_all(selector)

#         if not buttons:
#             break

#         clicked_any = False

#         for btn in buttons:
#             if btn.is_visible():
#                 btn.click()
#                 page.wait_for_timeout(delay)
#                 clicked_any = True

#         if not clicked_any:
#             break


def click_pagination_until_end_multiple_same_selectors(page, selector, delay=2000):
    """
    Clicks ALL matching selectors ONCE.
    Works even when markup is identical.
    """
    clicked_indexes = set()

    while True:
        buttons = page.query_selector_all(selector)
        clicked_any = False

        for idx, btn in enumerate(buttons):
            if idx in clicked_indexes:
                continue

            if btn.is_visible():
                btn.click()
                page.wait_for_timeout(delay)
                clicked_indexes.add(idx)
                clicked_any = True

        if not clicked_any:
            break



def click_pagination_until_end(page, selector, delay=2000):
    """
    Clicks a given selector repeatedly until it disappears or becomes invisible.
    """
    while True:
        try:
            button = page.query_selector(selector)
            if not button or not button.is_visible():
                break
            button.click()
            page.wait_for_timeout(delay)  # wait for content to load
        except Exception as e:
            print(f"⚠️ Error while clicking pagination: {e}")
            break



import re
# Where previous and next have identical selectors
def click_pagination_until_end2(page, selector, delay=2000):
    """
    Clicks the 'next page' button repeatedly until it disappears or becomes invisible.
    Works for CSS or XPath selectors.
    Skips buttons that look like 'previous/back'.
    """
    while True:
        try:
            # Support XPath or CSS
            if selector.strip().startswith("//"):
                button = page.locator(f"xpath={selector}").first
            else:
                button = page.locator(selector).first

            if not button or not button.is_visible():
                break

            # Avoid "previous" type buttons
            text = button.inner_text().strip().lower()
            if re.search(r"(prev|previous|back)", text):
                break

            button.click()
            page.wait_for_timeout(delay)

        except Exception as e:
            print(f"⚠️ Error while clicking pagination: {e}")
            break



def handle_numbered_pagination(page, selector, delay=2000):
    """
    Handles numbered pagination by clicking sequential page links (or navigating).
    Stops when next page link disappears or becomes inactive.
    """
    clicked_any = False
    html_parts = []
    page_number = 1
    while True:
        print(f"Visiting page {page_number}...")
        # Save or do something with current page content here if needed
        html_parts.append(page.content())
        next_page = page.query_selector(selector)
        if not next_page or not next_page.is_visible():
            print("No more pages found.")
            break
        
        try:
            next_page.click()
            page.wait_for_timeout(delay)  # wait for the page to load content
            page_number += 1
            clicked_any = True
        except Exception as e:
            print(f"⚠️ Error clicking numbered pagination: {e}")
            break

    combined_html = "\n<!-- PAGE BREAK -->\n".join(html_parts)
    return combined_html



# Function to capture JSON responses
def capture_json_responses(page):
    json_responses = []

    # Intercept network requests
    def handle_request(route):
        # Allow the request to go through
        route.continue_()

    def handle_response(response):
        if "application/json" in response.headers.get("content-type", ""):
            print("yes")
            json_responses.append(response.url)

    # Add event listeners
    page.on("route", handle_request)
    page.on("response", handle_response)

    return json_responses



def click_load_more(page, button_selector):
    while True:
        btn = page.query_selector(button_selector)
        if not btn or not btn.is_visible():
            print("No more 'Load More' button found.")
            break

        old_count = page.locator(".search-list__item").count()
        print(f"Current items: {old_count}")

        btn.click()

        try:
            # Wait until new items appear
            page.wait_for_function(
                """
                (oldCount) => {
                    const items = document.querySelectorAll('.search-list__item');
                    return items.length > oldCount;
                }
                """,
                old_count,
                timeout=10000
            )
            print("New items loaded!")
        except:
            print("No more new items loaded. Stopping.")
            break



from playwright.sync_api import sync_playwright

# @measure_time
def get_page_html(url,selector=None,save_path = None,numbered_pagination = False,load_more = False,infinite = False,multiple_same_selectors = False):


    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            # browser = p.chromium.launch_persistent_context(
            #         user_data_dir="user_data",
            #         headless=True,
            #         viewport={"width": 1366, "height": 768},
            #         args=[
            #             "--start-maximized"
            #         ]
            #     )
            page = browser.new_page()


            # page.mouse.move(
            #     random.randint(100, 800),
            #     random.randint(100, 600),
            #     steps=25
            # )

            page.wait_for_timeout(random.randint(800, 1500))

            # Capture JSON responses before navigating to the URL
            # json_responses = capture_json_responses(page)


           # Wait for initial JS content to load
            # page.goto(url, wait_until="domcontentloaded", timeout=100000)

            page.goto(url, wait_until="networkidle", timeout=200000)

            handle_cookie(page)
            
            if infinite:
                try:
                    auto_scroll_fixed(page)
                    page.wait_for_timeout(5000)
                    combined_html = page.content()
                except Exception as e:
                    print(f"An error occurred during scrolling: {e}")


            elif numbered_pagination:
                print("Trying numbered pagination first...")
                combined_html = handle_numbered_pagination(page, selector)


            elif load_more and multiple_same_selectors:
                print("Load more True and multiple same selectors")
                click_pagination_until_end_multiple_same_selectors(page, selector)
                combined_html = page.content()
                
            # If we got a pagination selector, click it until no more results
            elif load_more:
                print("Load more True")
                click_pagination_until_end(page, selector)
                combined_html = page.content()

            

            else:
                print("Entered auto scroll until end")
                auto_scroll_until_end(page)
                combined_html = page.content()


            # ⏳ Optional small wait after scroll , 10 seconds
            page.wait_for_timeout(10000)

        

            if save_path:
                # Save HTML to file
                Path(save_path).write_text(combined_html, encoding="utf-8")
                print(f"✅ HTML saved to {save_path}")


            browser.close()
    except Exception as e:
        print(f"An error occurred: {e}")

    # print(f"json responses:\n{json_responses}")
    return combined_html



if __name__ == "__main__":
    from datetime import datetime
    from datetime import timezone as tmz
    timestamp = datetime.now(tmz.utc).strftime("%H-%M-%S")

   

    # working !
    url = "https://www.squirepattonboggs.com/our-people?PageNumber=1"
    html = get_page_html(url)


    