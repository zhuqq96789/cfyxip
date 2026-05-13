from playwright.sync_api import sync_playwright
import time
import os

def get_all_domains():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--ignore-certificate-errors',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu'
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            ignore_https_errors=True,
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()
        
        try:
            print("正在访问页面...")
            page.goto("https://vps789.com/cfip/?remarks=domain", timeout=60000, wait_until="networkidle")
            
            # 等待表格出现
            page.wait_for_selector(".el-table__row", timeout=30000)
            print("表格已加载")
            
            all_domains = set()
            
            # 获取当前页数据
            def get_current_page_domains():
                return page.evaluate("""
                    () => {
                        const rows = document.querySelectorAll('.el-table__row');
                        const domains = [];
                        rows.forEach(row => {
                            const cells = row.querySelectorAll('td');
                            if (cells.length > 0) {
                                const text = cells[0].innerText.trim();
                                if (text) domains.push(text);
                            }
                        });
                        return domains;
                    }
                """)
            
            # 获取总条数
            total_count = page.evaluate("""
                () => {
                    const el = document.querySelector('.el-pagination__total');
                    if (el) {
                        const match = el.innerText.match(/\\d+/g);
                        return match ? parseInt(match[match.length - 1]) : 0;
                    }
                    return 0;
                }
            """)
            print(f"总数据量: {total_count} 条")
            
            # 初始数据
            current_domains = get_current_page_domains()
            all_domains.update(current_domains)
            print(f"第1页: {len(current_domains)} 条")
            
            page_num = 1
            max_pages = 100  # 加大上限
            
            while page_num < max_pages:
                # 检查是否最后一页
                is_last_page = page.evaluate("""
                    () => {
                        const nextBtn = document.querySelector('.btn-next');
                        return nextBtn ? nextBtn.classList.contains('disabled') || nextBtn.disabled : true;
                    }
                """)
                
                if is_last_page:
                    print("已到最后一页")
                    break
                
                # 点击下一页
                try:
                    next_button = page.query_selector('.btn-next')
                    if not next_button:
                        print("找不到下一页按钮")
                        break
                    
                    # 记录点击前的数据
                    old_domains = get_current_page_domains()
                    
                    next_button.click()
                    
                    # 等待新数据加载 - 关键改进
                    # 等待表格行数据发生变化
                    try:
                        page.wait_for_function("""
                            (oldFirst) => {
                                const rows = document.querySelectorAll('.el-table__row');
                                if (rows.length === 0) return false;
                                const first = rows[0].querySelector('td:first-child');
                                return first && first.innerText.trim() && first.innerText.trim() !== oldFirst;
                            }
                        """, arg=old_domains[0] if old_domains else "", timeout=15000)
                    except:
                        # 如果 wait_for_function 超时，额外等待
                        print("等待数据变化超时，尝试额外等待...")
                        time.sleep(3)
                    
                    # 再等一会确保渲染完成
                    page.wait_for_timeout(2000)
                    
                    # 获取新页数据
                    new_domains = get_current_page_domains()
                    
                    if not new_domains:
                        print("未获取到新数据")
                        break
                    
                    # 检查是否有数据变化
                    if set(new_domains) == set(old_domains):
                        print("数据未变化，可能翻页失败")
                        # 再等一会重试
                        time.sleep(3)
                        new_domains = get_current_page_domains()
                        if set(new_domains) == set(old_domains):
                            print("确认翻页失败，停止")
                            break
                    
                    all_domains.update(new_domains)
                    page_num += 1
                    print(f"第{page_num}页: {len(new_domains)} 条")
                    
                    # 检查是否达到总数
                    if total_count > 0 and len(all_domains) >= total_count:
                        print(f"已获取全部 {total_count} 条数据")
                        break
                    
                except Exception as e:
                    print(f"翻页错误: {e}")
                    break
            
            # 保存结果
            domain_list = sorted(list(all_domains))
            current_dir = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(current_dir, "domains.txt")
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(domain_list))
            
            print(f"✅ 最终提取完成！共抓取到 {len(domain_list)} 个唯一域名")
            return domain_list
            
        except Exception as e:
            print(f"❌ 错误: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            browser.close()

if __name__ == "__main__":
    get_all_domains()
