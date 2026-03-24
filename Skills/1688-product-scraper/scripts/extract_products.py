from playwright.sync_api import sync_playwright
import time
import re

products_data = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    print("打开1688页面...", flush=True)
    page.goto('https://air.1688.com/app/channel-fe/search/index.html#/result?spm=a260k.home2025.leftmenu_COLLAPSE.dfenxiaoxuanpin0of0fenxiao', timeout=120000)
    time.sleep(3)

    print("应用筛选条件...", flush=True)
    try:
        page.locator('text=拼多多').first.click()
        time.sleep(1)
    except:
        pass

    try:
        page.locator('text=包邮').first.click()
        time.sleep(1)
    except:
        pass

    try:
        page.locator('text=一件代发').first.click()
        time.sleep(1)
    except:
        pass

    time.sleep(3)

    current_page = 1
    max_pages = 20

    while len(products_data) < 3 and current_page <= max_pages:
        print(f"\n=== 浏览第 {current_page} 页 ===", flush=True)

        # 滚动加载当前页商品
        for i in range(5):
            page.evaluate("window.scrollBy(0, 800)")
            time.sleep(0.5)

        # 使用JavaScript提取所有商品信息
        products_on_page = page.evaluate("""
        () => {
            const items = document.querySelectorAll('a.fx-offer-card');
            const products = [];
            items.forEach(item => {
                try {
                    const href = item.getAttribute('href');
                    const title = item.querySelector('.offer-body__title')?.textContent || '';
                    const priceNum = item.querySelector('.price-number')?.textContent || '0';
                    const priceDecimal = item.querySelector('.price-decimal')?.textContent || '';
                    const price = parseFloat(priceNum + priceDecimal);
                    const deliveryText = item.innerText;

                    if (href && title) {
                        products.push({
                            href,
                            title,
                            price,
                            deliveryText
                        });
                    }
                } catch(e) {}
            });
            return products;
        }
        """)

        print(f"当前页找到 {len(products_on_page)} 个商品", flush=True)

        for prod in products_on_page:
            if len(products_data) >= 3:
                break

            try:
                href = prod['href']
                title = prod['title'].strip()
                price = prod['price']
                delivery_text = prod['deliveryText']

                # 检查是否是户外运动小件
                outdoor_keywords = ['网球', '羽毛球', '乒乓球', '跳绳', '护腕', '护膝', '运动', '健身', '瑜伽', '游泳', '登山', '骑行', '帐篷', '睡袋', '水壶', '背包', '手套', '帽子', '眼镜', '口哨', '指南针']
                is_outdoor = any(keyword in title for keyword in outdoor_keywords)

                if not is_outdoor:
                    continue

                # 提取近7天代发
                days7_match = re.search(r'近7天代发(\d+)([k+]*)', delivery_text)
                days7 = days7_match.group(1) + (days7_match.group(2) or '') if days7_match else ''

                # 转换为数字
                if 'k' in days7:
                    days7_num = int(days7.replace('k', '').replace('+', '')) * 1000
                else:
                    days7_num = int(days7.replace('+', '')) if days7 else 0

                # 检查条件：10-100元，近7天代发>=1K
                if 10 <= price <= 100 and days7_num >= 1000:
                    print(f"✓ 符合条件!", flush=True)
                    print(f"  链接: {href}", flush=True)

                    products_data.append({
                        'name': title,
                        'price': price,
                        'days7': days7,
                        'link': href
                    })

            except Exception as e:
                pass

        # 翻页
        if len(products_data) < 3:
            try:
                next_button = page.locator('text=下一页').or_(page.locator('[class*="next"]'))
                if next_button.count() > 0:
                    next_button.first.click()
                    time.sleep(3)
                    current_page += 1
                else:
                    print("没有下一页了", flush=True)
                    break
            except Exception as e:
                print(f"翻页失败: {e}", flush=True)
                break

    print(f"\n=== 最终结果 ===", flush=True)
    print(f"找到 {len(products_data)} 个符合条件的户外运动商品\n", flush=True)

    for i, prod in enumerate(products_data, 1):
        print(f"商品 {i}:", flush=True)
        print(f"  名称: {prod['name']}", flush=True)
        print(f"  价格: ￥{prod['price']}", flush=True)
        print(f"  近7天代发: {prod['days7']}", flush=True)
        print(f"  链接: {prod['link']}", flush=True)
        print()

    browser.close()

print("完成!", flush=True)
