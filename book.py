"""
Tennis Court Auto-Booking Script
Runs inside GitHub Actions at midnight WIB (00:00 UTC+7).
No local server or open browser needed.
"""

import json, os, time
from datetime import datetime, date
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

# ── Config ────────────────────────────────────────────────────────────────
BOOKING_EMAIL = os.environ.get("BOOKING_EMAIL", "hanchoo@gmail.com")
SCHEDULE_FILE = Path(__file__).parent / "schedule.json"

COURT_URLS = {
    1: "https://calendar.google.com/calendar/u/0/appointments/schedules/AcZssZ2y-UCm6xL7xhvVWiKOxqZJa6vyaUHbi50X4bGfSDwTmcQDyTUwi_fqvi-2vYH18hkcIUJ3wcNm?gv=true",
    2: "https://calendar.google.com/calendar/u/0/appointments/schedules/AcZssZ0khaHwW9_DvWBFmCUhpHe-khaGLq7zajAeXNPbBppNFwGMPzSzl_oI5fdBe9iZI2jKtJcYDUMs?gv=true",
    3: "https://calendar.google.com/calendar/u/0/appointments/schedules/AcZssZ0iQu6Dovr-zBRgHz84quFU_cU5yBF92sPqrjwORGKt7XSOls9zMKtESFV4rllRTDQnPO1j665j?gv=true",
}

MONTHS = ["January","February","March","April","May","June",
          "July","August","September","October","November","December"]

# ── Helpers ───────────────────────────────────────────────────────────────
def fmt_display(hour: int, minute: int = 0) -> str:
    ampm = "am" if hour < 12 else "pm"
    h    = 12 if hour == 0 else (hour - 12 if hour > 12 else hour)
    return f"{h}:{'00' if minute == 0 else str(minute).zfill(2)}{ampm}"

def react_set(driver, el, value: str):
    driver.execute_script("""
        var el=arguments[0],v=arguments[1];
        Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')
              .set.call(el,v);
        el.dispatchEvent(new Event('input',  {bubbles:true}));
        el.dispatchEvent(new Event('change', {bubbles:true}));
    """, el, value)

def find_input_by_label(driver, label_text: str):
    try:
        for lbl in driver.find_elements(By.TAG_NAME, "label"):
            if label_text.lower() not in (lbl.text or "").lower():
                continue
            fid = lbl.get_attribute("for")
            if fid:
                try: return driver.find_element(By.ID, fid)
                except: pass
            try: return lbl.find_element(By.CSS_SELECTOR, "input,textarea")
            except: pass
            result = driver.execute_script("""
                var l=arguments[0],s=l.nextElementSibling;
                while(s){var i=s.matches('input,textarea')?s:s.querySelector('input,textarea');
                         if(i)return i;s=s.nextElementSibling;}
                var p=l.parentElement;
                if(p){var ps=p.nextElementSibling;
                      while(ps){var i2=ps.matches('input,textarea')?ps:ps.querySelector('input,textarea');
                                if(i2)return i2;ps=ps.nextElementSibling;}}
                return null;
            """, lbl)
            if result: return result
    except: pass
    return None

# ── Core booking ──────────────────────────────────────────────────────────
def book_court(court_num: int, date_str: str, time_str: str) -> str:
    year, month, day = map(int, date_str.split("-"))
    hour, minute     = map(int, time_str.split(":"))
    display_time     = fmt_display(hour, minute)
    target_month     = MONTHS[month - 1]

    print(f"\n>>> Booking Court {court_num} | {date_str} | {display_time}")

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1400,900")

    driver = webdriver.Chrome(options=opts)   # Selenium Manager handles chromedriver
    wait   = WebDriverWait(driver, 15)

    try:
        print("  Loading booking page...")
        driver.get(COURT_URLS[court_num])
        time.sleep(3.5)

        # Navigate mini calendar to correct month
        for _ in range(18):
            header = driver.execute_script("""
                    var re=/^(January|February|March|April|May|June|July|August|September|October|November|December)\\s+\\d{4}$/;
                for(var el of document.querySelectorAll('h2,h3,[role="heading"]')){
                    var t=(el.textContent||'').trim();
                    if(re.test(t))return t;
                }return null;
            """)
            print(f"  Calendar: {header}")
            if header and target_month in header and str(year) in header:
                break
            clicked = driver.execute_script("""
                for(var b of document.querySelectorAll('button')){
                    var l=(b.getAttribute('aria-label')||'').toLowerCase();
                    var t=b.textContent.trim();
                    if((l.includes('next')||t==='>'||t==='›')&&!b.disabled){b.click();return true;}
                }return false;
            """)
            if not clicked:
                raise RuntimeError("Cannot navigate calendar")
            time.sleep(0.6)

        # Click target date
        result = driver.execute_script("""
            var d=arguments[0],m=arguments[1],y=arguments[2];
            var exp=m+' '+d+', '+y;
            for(var b of document.querySelectorAll('button')){
                if((b.getAttribute('aria-label')||'').includes(exp)&&!b.disabled){b.click();return 'aria';}
            }
            for(var b of document.querySelectorAll('button')){
                if(b.textContent.trim()===String(d)&&!b.disabled&&b.offsetParent){b.click();return 'text';}
            }
            return null;
        """, day, target_month, year)
        if not result:
            raise RuntimeError(f"Date {day} not found in calendar")
        print(f"  Clicked date ({result})")
        time.sleep(2.5)

        # Click time slot
        found = False
        for _ in range(12):
            found = driver.execute_script("""
                var t=arguments[0];
                for(var b of document.querySelectorAll('button')){
                    if(b.textContent.trim().toLowerCase()===t.toLowerCase()&&!b.disabled){
                        b.click();return true;
                    }
                }return false;
            """, display_time)
            if found: break
            time.sleep(1.0)
        if not found:
            driver.save_screenshot("screenshot_debug.png")
            raise RuntimeError(
                f'"{display_time}" not available — slot may be outside the 72-hour window or already booked.'
            )
        print(f"  Clicked time: {display_time}")
        time.sleep(2.5)

        # Wait for form
        wait.until(lambda d: len(d.find_elements(
            By.CSS_SELECTOR, 'input[type="text"],input:not([type])')) >= 2)
        time.sleep(0.5)

        # Fill all fields
        all_inp = driver.execute_script("""
            return Array.from(document.querySelectorAll('input[type="text"],input:not([type])'))
                        .filter(e=>e.offsetParent);
        """)

        fn    = find_input_by_label(driver, "first name")  or (all_inp[0] if len(all_inp)>0 else None)
        ln    = find_input_by_label(driver, "last name")   or (all_inp[1] if len(all_inp)>1 else None)
        email = find_input_by_label(driver, "email")       or (all_inp[2] if len(all_inp)>2 else None)
        jis   = find_input_by_label(driver, "JIS")         or (all_inp[3] if len(all_inp)>3 else None)

        if fn:    react_set(driver, fn,    "Tennis")
        if ln:    react_set(driver, ln,    "Singles")
        if email: react_set(driver, email, BOOKING_EMAIL)
        if jis:   react_set(driver, jis,   "C")
        print(f"  Form filled (email: {BOOKING_EMAIL})")
        time.sleep(1.2)

        # Click Book
        booked = driver.execute_script("""
            for(var b of document.querySelectorAll('button')){
                if(b.textContent.trim()==='Book'&&!b.disabled){b.click();return true;}
            }return false;
        """)
        if not booked:
            raise RuntimeError("Book button not found")
        print("  Clicked Book!")
        time.sleep(6)

        body = driver.find_element(By.TAG_NAME, "body").text.lower()
        ok   = any(w in body for w in ("confirmed","booked","scheduled","thank"))
        print(f"  Confirmation on page: {ok}")

        return f"Court {court_num} booked for {date_str} at {display_time}. Check your email."

    finally:
        time.sleep(1)
        try: driver.quit()
        except: pass

# ── Main: process due bookings ────────────────────────────────────────────
def main():
    with open(SCHEDULE_FILE) as f:
        bookings = json.load(f)

    today = date.today()
    changed = False
    ran = 0

    for b in bookings:
        if b["status"] not in ("pending", "queued"):
            continue
        run_at = datetime.fromisoformat(b["run_at"]).date()
        if run_at > today:
            print(f"  Skipping Court {b['court']} {b['date']} — runs {run_at}")
            continue

        ran += 1
        print(f"\n=== Running booking: Court {b['court']} | {b['date']} | {b['time']} ===")
        try:
            msg = book_court(b["court"], b["date"], b["time"])
            b["status"]       = "success"
            b["message"]      = msg
        except Exception as e:
            b["status"]       = "failed"
            b["message"]      = str(e)
            print(f"  ERROR: {e}")
        b["completed_at"] = datetime.now().isoformat()
        changed = True

    if ran == 0:
        print("No bookings due today.")

    if changed:
        with open(SCHEDULE_FILE, "w") as f:
            json.dump(bookings, f, indent=2)
        print(f"\nUpdated {SCHEDULE_FILE}")

if __name__ == "__main__":
    main()
