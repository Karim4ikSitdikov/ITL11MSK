import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import xml.etree.ElementTree as ET
import time
import re
from config import Config


class StolotoParser:
    """Parser for Stoloto lottery data"""
    
    def __init__(self):
        self.base_url = 'https://www.stoloto.ru'
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': Config.USER_AGENT
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
                    if '/loto/' in loc.text or '/instant/' in loc.text:
                        urls.append(loc.text)
            
            print(f"Found {len(urls)} lottery URLs in sitemap")
            return urls
            
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
    
    def parse_draw_archive(self, url: str, lottery_id: int) -> List[Dict]:
        """
        Parse draw archive page to extract historical draw results
        
        Returns:
            List of draw data dictionaries
        """
        try:
            time.sleep(self.request_delay)
            
            response = self.session.get(url, timeout=Config.REQUEST_TIMEOUT)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            draws = []
            
            # This is a simplified parser - actual implementation would need
            # to be customized based on Stoloto's actual HTML structure
            # Look for draw containers
            draw_containers = soup.find_all(class_=re.compile(r'draw|archive|result', re.I))
            
            for container in draw_containers[:50]:  # Limit to 50 draws per page
                draw_data = self._extract_draw_data(container, lottery_id)
                if draw_data:
                    draws.append(draw_data)
            
            print(f"Parsed {len(draws)} draws from archive")
            return draws
            
        except Exception as e:
            print(f"Error parsing draw archive {url}: {e}")
            return []
    
    def _extract_draw_data(self, container, lottery_id: int) -> Optional[Dict]:
        """Extract draw data from a container element"""
        try:
            # Extract draw number
            draw_number = None
            number_elem = container.find(text=re.compile(r'№?\s*(\d+)'))
            if number_elem:
                match = re.search(r'(\d+)', str(number_elem))
                if match:
                    draw_number = int(match.group(1))
            
            # Extract date
            draw_date = None
            date_elem = container.find(text=re.compile(r'\d{2}\.\d{2}\.\d{4}'))
            if date_elem:
                draw_date = str(date_elem).strip()
            
            # Extract winning numbers
            winning_numbers = []
            number_elems = container.find_all(class_=re.compile(r'number|ball|digit', re.I))
            for elem in number_elems:
                text = elem.get_text(strip=True)
                if text.isdigit():
                    winning_numbers.append(text)
            
            if draw_number:
                return {
                    'lottery_id': lottery_id,
                    'draw_number': draw_number,
                    'draw_date': draw_date,
                    'winning_numbers': ','.join(winning_numbers) if winning_numbers else None,
                    'total_prize_fund': None,  # Would need more specific parsing
                    'winners_count': 0
                }
            
            return None
            
        except Exception as e:
            print(f"Error extracting draw data: {e}")
            return None


if __name__ == '__main__':
    # Test parser
    parser = StolotoParser()
    
    print("Testing Stoloto parser...")
    print("\n1. Parsing main sitemap...")
    lottery_urls = parser.parse_sitemap_main()
    print(f"Found {len(lottery_urls)} lottery URLs")
    
    if lottery_urls:
        print(f"\nSample URLs:")
        for url in lottery_urls[:5]:
            print(f"  - {url}")
    
    print("\n2. Parsing archive sitemap...")
    archive_urls = parser.parse_sitemap_archive()
    print(f"Found {len(archive_urls)} archive URLs")
    
    if archive_urls:
        print(f"\nSample archive URLs:")
        for url in archive_urls[:3]:
            print(f"  - {url}")
    
    # Uncomment to test actual page parsing (requires working URLs)
    # if lottery_urls:
    #     print("\n3. Testing lottery page parsing...")
    #     lottery_data = parser.parse_lottery_page(lottery_urls[0])
    #     if lottery_data:
    #         print(f"Lottery data: {lottery_data}")
