import argparse
from datetime import datetime
import json
import os
import random
import re
import time
from bs4 import BeautifulSoup
import pandas as pd
from playwright.sync_api import sync_playwright

SESSION_FILE = "session.json"
TARGET_URL = "https://www.linkedin.com/company/nutifood-viet-nam/posts/"

def decode_linkedin_timestamp(urn):
    """
    Giải mã ID bài viết LinkedIn thành thời gian tuyệt đối (Định dạng YYYY-MM-DD HH:MM:SS)
    """
    try:
        match = re.search(r'(\d{19})', str(urn))
        if not match:
            match = re.search(r'(\d+)', str(urn))
        if match:
            post_id = int(match.group(1))
            binary_id = bin(post_id)[2:]
            first_41_bits = binary_id[:41]
            timestamp_ms = int(first_41_bits, 2)
            timestamp_s = timestamp_ms / 1000.0
            dt = datetime.fromtimestamp(timestamp_s)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        pass
    return ""

def parse_count(text):
    """
    Chuyển đổi các chuỗi tương tác (ví dụ: '1.2K', '5,600 comments') thành số nguyên
    """
    if not text:
        return 0
    text = text.lower().strip()
    # Tìm kiếm mẫu số và hậu tố k/m
    match = re.search(r'([\d.,]+)\s*([km]?)', text)
    if not match:
        return 0
    num_str = match.group(1).replace(',', '')
    multiplier = match.group(2)
    try:
        val = float(num_str)
        if multiplier == 'k':
            val *= 1000
        elif multiplier == 'm':
            val *= 1000000
        return int(val)
    except ValueError:
        return 0

def run_login():
    """
    Mở trình duyệt ở chế độ hiển thị để người dùng đăng nhập thủ công,
    sau đó lưu trạng thái session vào tệp session.json.
    """
    print("==================================================")
    print("BẮT ĐẦU QUÁ TRÌNH ĐĂNG NHẬP")
    print("==================================================")
    print("1. Trình duyệt Chromium sẽ mở ra.")
    print("2. Vui lòng đăng nhập vào tài khoản LinkedIn của bạn.")
    print("3. Giải quyết mã CAPTCHA hoặc xác thực 2 lớp (2FA) nếu được yêu cầu.")
    print("4. Sau khi đăng nhập thành công và nhìn thấy bảng tin (Feed) cá nhân,")
    print("   hãy quay lại màn hình terminal này và nhấn [ENTER] để lưu phiên đăng nhập.")
    print("==================================================")
    
    with sync_playwright() as p:
        # Mở trình duyệt có giao diện (headless=False)
        browser = p.chromium.launch(headless=False)
        # Tạo context mới
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        page = context.new_page()
        page.goto("https://www.linkedin.com/login")
        
        # Đợi người dùng nhấn Enter tại Terminal
        input("\nSau khi đã đăng nhập thành công, nhấn [ENTER] tại đây để lưu session... ")
        
        # Lưu cookies và trạng thái lưu trữ
        storage = context.storage_state()
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(storage, f, ensure_ascii=False, indent=4)
        
        print(f"\n[THÀNH CÔNG] Đã lưu thông tin đăng nhập vào file '{SESSION_FILE}'!")
        browser.close()

def format_company_posts_url(url):
    """
    Chuẩn hóa URL của công ty trên LinkedIn thành URL trang bài viết (posts)
    """
    url = url.strip()
    if "?" in url:
        url = url.split("?")[0]
    if not url.endswith("/"):
        url += "/"
    if not url.endswith("/posts/"):
        if "/company/" in url:
            parts = url.rstrip("/").split("/company/")
            company_id = parts[1].split("/")[0]
            url = f"https://www.linkedin.com/company/{company_id}/posts/"
    return url

def get_company_slug(url):
    """
    Trích xuất tên rút gọn (slug) của công ty từ URL
    """
    match = re.search(r'/company/([^/]+)', url)
    if match:
        return match.group(1)
    return "company"

def run_scrape(target_url, limit, output_name):
    """
    Tải session đã lưu, truy cập trang doanh nghiệp, cuộn trang để tải bài viết,
    trích xuất dữ liệu và lưu vào CSV/JSON.
    """
    if not os.path.exists(SESSION_FILE):
        print(f"[LỖI] Không tìm thấy file '{SESSION_FILE}'! Vui lòng chạy lệnh đăng nhập trước:")
        print("  python scraper.py --login")
        return

    # Chuẩn hóa URL mục tiêu
    target_url = format_company_posts_url(target_url)
    company_slug = get_company_slug(target_url)
    
    # Thiết lập tên đầu ra mặc định nếu không truyền hoặc trùng mặc định cũ
    if not output_name or output_name == "vinamilk_posts":
        output_name = f"{company_slug}_posts"

    print("==================================================")
    print(f"BẮT ĐẦU CÀO DỮ LIỆU BÀI VIẾT: {company_slug.upper()} (Giới hạn: {limit} bài)")
    print(f"URL mục tiêu: {target_url}")
    print("==================================================")

    with sync_playwright() as p:
        # Chạy ẩn danh (headless=True), nhưng bạn có thể chỉnh thành False để debug
        browser = p.chromium.launch(headless=False) 
        
        # Tạo context bằng cách tải trạng thái session cũ
        context = browser.new_context(
            storage_state=SESSION_FILE,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        page = context.new_page()
        
        # Đặt kích thước màn hình
        page.set_viewport_size({"width": 1280, "height": 800})
        
        print(f"Đang truy cập trang posts của công ty: {target_url}")
        page.goto(target_url)
        page.wait_for_timeout(3000)
        
        # Kiểm tra xem có bị bắt đăng nhập lại không
        if "login" in page.url:
            print("[LỖI] Session của bạn đã hết hạn hoặc không hợp lệ. Vui lòng đăng nhập lại bằng lệnh:")
            print("  python scraper.py --login")
            browser.close()
            return

        print("Đang cuộn trang để tải bài viết. Vui lòng đợi...")
        
        scroll_count = 0
        max_scrolls = limit * 3  # Giới hạn số lần cuộn tránh lặp vô hạn
        posts_loaded = 0
        
        # Vòng lặp cuộn trang từng bước
        while posts_loaded < limit and scroll_count < max_scrolls:
            # Lấy chiều cao trang trước khi cuộn
            last_height = page.evaluate("document.body.scrollHeight")
            
            # Cuộn từng bước nhỏ từ vị trí hiện tại xuống cuối trang để kích hoạt lazy loading
            current_position = page.evaluate("window.pageYOffset")
            step = 1000
            while current_position < last_height:
                next_position = min(current_position + step, last_height)
                page.evaluate(f"window.scrollTo(0, {next_position})")
                current_position = next_position
                page.wait_for_timeout(random.randint(400, 800))
                
            # Đợi thêm một chút để trang tải dữ liệu mới
            page.wait_for_timeout(random.randint(2000, 3000))
            
            # Kiểm tra và nhấn nút "Show more" hoặc "Xem thêm cập nhật" nếu xuất hiện ở cuối trang
            show_more_feed = page.locator("button:has-text('Show more'), button:has-text('Xem thêm cập nhật'), button:has-text('See more updates')")
            try:
                if show_more_feed.count() > 0 and show_more_feed.first.is_visible():
                    print("Phát hiện nút 'Xem thêm bài viết', đang click vào nút...")
                    show_more_feed.first.click(timeout=1000)
                    page.wait_for_timeout(2000)
            except Exception:
                pass
                
            # Click vào nút "Xem thêm" (See more) để mở rộng nội dung các bài viết đã tải
            see_more_buttons = page.locator("button.feed-shared-inline-show-more-text__see-more-less-toggle, button:has-text('see more'), button:has-text('Xem thêm')")
            btn_count = see_more_buttons.count()
            for i in range(btn_count):
                try:
                    btn = see_more_buttons.nth(i)
                    if btn.is_visible():
                        btn.click(timeout=500)
                except Exception:
                    pass
            
            # Lấy HTML hiện tại và đếm số lượng bài viết
            soup = BeautifulSoup(page.content(), "html.parser")
            post_elements = []
            seen_urns = set()
            for div in soup.find_all("div", attrs={"data-urn": True}):
                urn = div.get("data-urn", "")
                if any(x in urn for x in ["activity", "share", "ugcPost"]):
                    if urn not in seen_urns:
                        post_elements.append(div)
                        seen_urns.add(urn)
            
            posts_loaded = len(post_elements)
            print(f"Đã phát hiện: {posts_loaded} bài viết trên trang...")
            
            if posts_loaded >= limit:
                print(f"Đã tải đủ số bài viết yêu cầu ({posts_loaded} >= {limit}). Dừng cuộn.")
                break
                
            new_height = page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                # Nếu chiều cao không thay đổi, thử cuộn lên rồi xuống lại
                page.evaluate("window.scrollTo(0, document.body.scrollHeight - 800)")
                page.wait_for_timeout(1500)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(3000)
                new_height = page.evaluate("document.body.scrollHeight")
                if new_height == last_height:
                    # Đợi thêm một chút phòng khi mạng chậm
                    page.wait_for_timeout(3000)
                    new_height = page.evaluate("document.body.scrollHeight")
                    if new_height == last_height:
                        print("Đã đạt tới cuối trang bài viết hoặc không thể tải thêm.")
                        break
                    
            scroll_count += 1

        # Trích xuất dữ liệu chi tiết
        soup = BeautifulSoup(page.content(), "html.parser")
        post_elements = []
        seen_urns = set()
        for div in soup.find_all("div", attrs={"data-urn": True}):
            urn = div.get("data-urn", "")
            if any(x in urn for x in ["activity", "share", "ugcPost"]):
                if urn not in seen_urns:
                    post_elements.append(div)
                    seen_urns.add(urn)

        # Giới hạn lại số lượng bài viết cần trích xuất dữ liệu
        post_elements = post_elements[:limit]
        
        extracted_posts = []
        print(f"\nBắt đầu phân tích cú pháp {len(post_elements)} bài viết...")
        
        for idx, post in enumerate(post_elements, 1):
            urn = post.get("data-urn", "")
            
            # 1. Đường dẫn bài viết
            post_url = f"https://www.linkedin.com/feed/update/{urn}"
            
            # 2. Nội dung văn bản
            text_elem = post.find(class_=lambda x: x and (
                'feed-shared-update-v2__description' in x or 
                'update-components-text' in x or 
                'feed-shared-text-view' in x
            ))
            post_text = ""
            if text_elem:
                post_text = text_elem.get_text(strip=True)
                # Loại bỏ chữ "see more" / "xem thêm" ở cuối nếu còn dính
                if post_text.endswith("...see more"):
                    post_text = post_text[:-11].strip()
                elif post_text.endswith("... Xem thêm"):
                    post_text = post_text[:-12].strip()
            
            # 3. Thời gian đăng bài (Thời gian tương đối)
            time_elem = post.find(class_=lambda x: x and (
                'update-components-actor__sub-text' in x or 
                'feed-shared-actor__sub-text' in x
            ))
            publish_time = ""
            if time_elem:
                # Thử tìm thẻ span có class visually-hidden trước
                hidden_span = time_elem.find(class_=lambda x: x and 'visually-hidden' in x)
                if hidden_span:
                    publish_time = hidden_span.get_text(strip=True)
                else:
                    # Nếu không tìm thấy, lấy toàn bộ văn bản và làm sạch
                    publish_time = time_elem.get_text(strip=True)
                    if '•' in publish_time:
                        publish_time = publish_time.split('•')[0].strip()
            
            # Giải mã thời gian tuyệt đối chính xác từ ID bài viết
            created_time = decode_linkedin_timestamp(urn)
            
            # 4. Hình ảnh đính kèm
            images = []
            for img in post.find_all("img"):
                src = img.get("src") or img.get("data-delayed-url")
                if src and "media.licdn.com/dms/image" in src:
                    # Loại bỏ ảnh avatar của Vinamilk
                    is_actor = False
                    for parent in img.parents:
                        if parent.name and hasattr(parent, "get"):
                            classes = parent.get("class") or []
                            classes_str = " ".join(classes) if isinstance(classes, list) else str(classes)
                            if any(x in classes_str for x in ['actor', 'profile', 'avatar', 'logo']):
                                is_actor = True
                                break
                    # Kiểm tra thêm thuộc tính alt để lọc avatar
                    alt = img.get("alt", "").lower()
                    if not is_actor and "vinamilk" not in alt:
                        images.append(src)
            
            # Lọc trùng hình ảnh
            images = list(set(images))
            
            # 5. Video đính kèm
            videos = []
            for video in post.find_all("video"):
                v_src = video.get("src")
                if v_src:
                    videos.append(v_src)
            
            # 6. Các chỉ số tương tác
            # Lượt thích/tim (Reactions)
            reactions_elem = post.find(class_=lambda x: x and 'social-details-social-counts__reactions-count' in x)
            if not reactions_elem:
                reactions_elem = post.find(class_=lambda x: x and 'social-details-social-counts__social-action-button' in x)
            reactions_text = reactions_elem.get_text(strip=True) if reactions_elem else "0"
            reactions_count = parse_count(reactions_text)
            
            # Lượt bình luận (Comments)
            comments_elem = post.find(class_=lambda x: x and 'social-details-social-counts__comments' in x)
            comments_text = comments_elem.get_text(strip=True) if comments_elem else "0"
            comments_count = parse_count(comments_text)
            
            # Lượt chia sẻ (Reposts / Shares)
            shares_elem = post.find(class_=lambda x: x and 'social-details-social-counts__shares' in x)
            shares_text = shares_elem.get_text(strip=True) if shares_elem else "0"
            shares_count = parse_count(shares_text)
            
            extracted_posts.append({
                "stt": idx,
                "urn": urn,
                "post_url": post_url,
                "created_time": created_time,
                "publish_time": publish_time,
                "content": post_text,
                "images": ", ".join(images) if images else "",
                "videos": ", ".join(videos) if videos else "",
                "reactions_count": reactions_count,
                "comments_count": comments_count,
                "shares_count": shares_count
            })
            
        # Lưu kết quả
        df = pd.DataFrame(extracted_posts)
        
        json_file = f"{output_name}.json"
        csv_file = f"{output_name}.csv"
        
        # Xuất dữ liệu
        df.to_json(json_file, orient="records", force_ascii=False, indent=4)
        df.to_csv(csv_file, index=False, encoding="utf-8-sig")
        
        print("\n==================================================")
        print("[THÀNH CÔNG] Quá trình cào dữ liệu hoàn tất!")
        print(f"Tổng số bài viết đã lưu: {len(extracted_posts)}")
        print(f"Đường dẫn file JSON: {os.path.abspath(json_file)}")
        print(f"Đường dẫn file CSV: {os.path.abspath(csv_file)}")
        print("==================================================")
        
        browser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cào dữ liệu bài viết LinkedIn của các công ty bằng Python")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--login", action="store_true", help="Mở trình duyệt để đăng nhập thủ công và lưu session")
    group.add_argument("--scrape", action="store_true", help="Chạy cào dữ liệu sử dụng session đã lưu")
    
    parser.add_argument("--url", type=str, default="https://www.linkedin.com/company/vinamilk/posts/", help="Đường dẫn đến trang LinkedIn của công ty")
    parser.add_argument("--limit", type=int, default=1000, help="Giới hạn số lượng bài viết cần lấy (mặc định: 1000)")
    parser.add_argument("--output", type=str, default=None, help="Tên file đầu ra (mặc định: tự động đặt theo tên công ty)")
    
    args = parser.parse_args()
    
    if args.login:
        run_login()
    elif args.scrape:
        run_scrape(args.url, args.limit, args.output)
