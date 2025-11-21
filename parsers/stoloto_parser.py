import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Any
import xml.etree.ElementTree as ET
import time
import re
import json
from config import Config


class StolotoParser:
    """Parser for Stoloto lottery data"""
    
    def __init__(self):
        self.base_url = 'https://www.stoloto.ru'
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': Config.USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
        })
        self.request_delay = Config.REQUEST_DELAY
    
    def parse_sitemap_main(self, url: str = 'https://www.stoloto.ru/sitemap_main.xml') -> List[str]:
        """
        Parse main sitemap to get lottery URLs
        
        Returns:
            List of lottery page URLs
        """
        try:
            response = self.session.get(url, timeout=Config.REQUEST_TIMEOUT)
            response.raise_for_status()
            
            # Parse XML
            root = ET.fromstring(response.content)
            
            # Extract URLs (namespace-aware)
            ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            urls = []
            
            for url_elem in root.findall('.//ns:url', ns):
                loc = url_elem.find('ns:loc', ns)
                if loc is not None and loc.text:
                    # Filter for lottery pages
                    if '/loto/' in loc.text or '/instant/' in loc.text or '/game' in loc.text:
                        urls.append(loc.text)
                    # Also include main lottery pages like /ruslotto, /4x20 etc if they are in sitemap
                    elif loc.text.count('/') == 3 and not 'archive' in loc.text:
                         urls.append(loc.text)
            
            print(f"Found {len(urls)} lottery URLs in sitemap")
            return list(set(urls)) # Deduplicate
            
        except Exception as e:
            print(f"Error parsing sitemap: {e}")
            return []
    
    def parse_sitemap_archive(self, url: str = 'https://www.stoloto.ru/sitemap_archive.xml') -> List[str]:
        """
        Parse archive sitemap to get draw archive URLs
        
        Returns:
            List of archive page URLs
        """
        try:
            response = self.session.get(url, timeout=Config.REQUEST_TIMEOUT)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            urls = []
            
            for url_elem in root.findall('.//ns:url', ns):
                loc = url_elem.find('ns:loc', ns)
                if loc is not None and loc.text:
                    if '/archive/' in loc.text:
                        urls.append(loc.text)
            
            print(f"Found {len(urls)} archive URLs in sitemap")
            return urls
            
        except Exception as e:
            print(f"Error parsing archive sitemap: {e}")
            return []
    
    def parse_lottery_page(self, url: str) -> Optional[Dict]:
        """
        Parse a lottery page to extract lottery information
        
        Returns:
            Dictionary with lottery data
        """
        try:
            time.sleep(self.request_delay)  # Rate limiting
            
            response = self.session.get(url, timeout=Config.REQUEST_TIMEOUT)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Extract lottery name
            name = None
            name_elem = soup.find('h1')
            if name_elem:
                name = name_elem.get_text(strip=True)
            
            # Determine lottery type from URL
            lottery_type = 'instant' if '/instant/' in url else 'draw'
            
            # Extract ticket price
            ticket_price = None
            price_patterns = [
                r'(\d+)\s*(?:руб|₽)',
                r'цена.*?(\d+)',
                r'стоимость.*?(\d+)'
            ]
            
            for pattern in price_patterns:
                price_match = re.search(pattern, response.text, re.IGNORECASE)
                if price_match:
                    ticket_price = float(price_match.group(1))
                    break
            
            # Extract description
            description = None
            desc_elem = soup.find('meta', {'name': 'description'})
            if desc_elem and desc_elem.get('content'):
                description = desc_elem.get('content')
            
            # Extract draw frequency (for draw lotteries)
            draw_frequency = None
            if lottery_type == 'draw':
                frequency_patterns = [
                    r'розыгрыш.*?(каждый день|ежедневно|раз в неделю|\d+ раза? в неделю)',
                    r'тираж.*?(каждый день|ежедневно|раз в неделю|\d+ раза? в неделю)'
                ]
                
                for pattern in frequency_patterns:
                    freq_match = re.search(pattern, response.text, re.IGNORECASE)
                    if freq_match:
                        draw_frequency = freq_match.group(1)
                        break
            
            # Extract max prize / jackpot
            max_prize = None
            prize_patterns = [
                r'джекпот.*?(\d[\d\s]+)',
                r'главный приз.*?(\d[\d\s]+)',
                r'максимальный выигрыш.*?(\d[\d\s]+)'
            ]
            
            for pattern in prize_patterns:
                prize_match = re.search(pattern, response.text, re.IGNORECASE)
                if prize_match:
                    prize_str = prize_match.group(1).replace(' ', '')
                    try:
                        max_prize = float(prize_str)
                    except:
                        pass
                    break
            
            # Create slug from URL
            slug = url.rstrip('/').split('/')[-1]
            if slug == 'game' or slug == 'about':
                 slug = url.rstrip('/').split('/')[-2]

            lottery_data = {
                'name': name or slug.replace('-', ' ').title(),
                'slug': slug,
                'lottery_type': lottery_type,
                'ticket_price': ticket_price,
                'draw_frequency': draw_frequency,
                'description': description,
                'max_prize': max_prize,
                'url': url,
                'is_active': True
            }
            
            print(f"Parsed lottery: {lottery_data['name']}")
            return lottery_data
            
        except Exception as e:
            print(f"Error parsing lottery page {url}: {e}")
            return None
    
    def parse_draw_page(self, url: str, lottery_id: int) -> Optional[Dict]:
        """
        Parse a specific draw page to extract results and prize distribution
        
        Returns:
            Dictionary with draw data and prize categories
        """
        try:
            time.sleep(self.request_delay)
            
            response = self.session.get(url, timeout=Config.REQUEST_TIMEOUT)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Try to extract data from __NEXT_DATA__
            next_data = self._extract_next_data(soup)
            
            if next_data:
                return self._parse_from_next_data(next_data, lottery_id)
            
            # Fallback to HTML parsing if needed (though unlikely to work for dynamic content)
            print(f"Warning: Could not find __NEXT_DATA__ in {url}")
            return None
            
        except Exception as e:
            print(f"Error parsing draw page {url}: {e}")
            return None

    def _extract_next_data(self, soup: BeautifulSoup) -> Optional[Dict]:
        """Extract JSON data from __NEXT_DATA__ script tag"""
        script = soup.find('script', id='__NEXT_DATA__')
        if script:
            try:
                return json.loads(script.string)
            except json.JSONDecodeError:
                return None
        return None

    def _parse_from_next_data(self, data: Dict, lottery_id: int) -> Optional[Dict]:
        """Parse draw data from Next.js state"""
        try:
            # Navigate to the relevant data
            page_props = data.get('props', {}).get('pageProps', {})
            queries = page_props.get('dehydratedState', {}).get('queries', [])
            
            best_draw_info = None
            best_score = -1
            
            # Iterate through all queries to find the best candidate for draw data
            for query in queries:
                query_key = query.get('queryKey', [])
                if isinstance(query_key, list) and len(query_key) > 0:
                    # Check if it looks like a draw query
                    is_draw_query = False
                    if query_key[0] == 'service-draws':
                        is_draw_query = True
                    elif isinstance(query_key[0], str) and 'draw' in query_key[0]:
                        is_draw_query = True
                    
                    if is_draw_query:
                        candidate_data = query.get('state', {}).get('data', {})
                        
                        # Handle list vs dict
                        if isinstance(candidate_data, list):
                            if not candidate_data:
                                continue
                            candidate_info = candidate_data[0]
                        else:
                            # Check for nested 'draw' object (common in some lotteries)
                            if 'draw' in candidate_data and isinstance(candidate_data['draw'], dict):
                                candidate_info = candidate_data['draw']
                            else:
                                candidate_info = candidate_data
                            
                        if not candidate_info:
                            continue
                            
                        # Score this candidate based on completeness
                        score = 0
                        if 'drawNumber' in candidate_info:
                            score += 1
                        if 'winCategories' in candidate_info:
                            score += 10
                        if 'winningNumbers' in candidate_info:
                            score += 10
                        if 'totalPrizeFund' in candidate_info:
                            score += 5
                            
                        if score > best_score:
                            best_score = score
                            best_draw_info = candidate_info

            # If we didn't find any good data in queries, check pageProps directly
            if not best_draw_info and 'drawNumber' in page_props:
                 # This is a fallback, likely just metadata
                 best_draw_info = page_props

            if not best_draw_info:
                return None

            draw_info = best_draw_info

            # Extract fields
            draw_number = draw_info.get('drawNumber')
            
            # Fallback for draw number if missing in data but present in pageProps
            if not draw_number:
                draw_number = page_props.get('drawNumber')

            draw_date = draw_info.get('drawDate') or draw_info.get('date') or page_props.get('drawDate')
            
            # Winning numbers
            winning_numbers = []
            if 'winningNumbers' in draw_info:
                 winning_numbers = draw_info['winningNumbers']
            
            # Prize categories
            prize_categories = []
            total_prize_fund = draw_info.get('totalPrizeFund') or draw_info.get('prizeFund')
            winners_count = 0
            
            if 'winCategories' in draw_info:
                for cat in draw_info['winCategories']:
                    cat_name = cat.get('title', {}).get('ru') or str(cat.get('number'))
                    prize = cat.get('amount')
                    winners = cat.get('participants')
                    
                    winners_count += winners if winners else 0
                    
                    prize_categories.append({
                        'category_name': cat_name,
                        'prize_amount': prize,
                        'winners_count': winners,
                        'probability': None 
                    })
                    
                    # For RusLotto/Housing, collect numbers from categories if main winning numbers are missing
                    if not winning_numbers and 'numbers' in cat:
                        winning_numbers.extend(cat['numbers'])

            if not draw_number:
                print("Warning: Could not extract draw_number")
                return None

            return {
                'lottery_id': lottery_id,
                'draw_number': draw_number,
                'draw_date': draw_date,
                'winning_numbers': json.dumps(winning_numbers),
                'total_prize_fund': total_prize_fund,
                'winners_count': winners_count,
                'prize_categories': prize_categories
            }

        except Exception as e:
            print(f"Error parsing Next.js data: {e}")
            return None

if __name__ == '__main__':
    # Test parser
    parser = StolotoParser()
    
    print("Testing Stoloto parser...")
    
    # Test specific draw parsing
    test_url = 'https://www.stoloto.ru/ruslotto/archive/1695'
    print(f"\nTesting draw parsing for {test_url}...")
    draw_data = parser.parse_draw_page(test_url, 1)
    
    if draw_data:
        print(f"Draw Number: {draw_data['draw_number']}")
        print(f"Date: {draw_data['draw_date']}")
        print(f"Prize Fund: {draw_data['total_prize_fund']}")
        print(f"Categories found: {len(draw_data['prize_categories'])}")
        if draw_data['prize_categories']:
            print(f"Sample category: {draw_data['prize_categories'][0]}")
    else:
        print("Failed to parse draw data")
