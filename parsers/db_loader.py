#!/usr/bin/env python3
"""
Database loader for Stoloto lottery data
Parses

 lottery data and loads it into PostgreSQL
"""

import sys
from parsers.stoloto_parser import StolotoParser
from database.db import Database
from datetime import datetime
import argparse


def load_lotteries():
    """Parse and load lottery data"""
    print("="*60)
    print("LOADING LOTTERY DATA")
    print("="*60)
    
    parser = StolotoParser()
    
    # Parse sitemap to get lottery URLs
    print("\n1. Fetching lottery URLs from sitemap...")
    lottery_urls = parser.parse_sitemap_main()
    
    if not lottery_urls:
        print("  ⚠ No lottery URLs found. Using fallback data.")
        lottery_urls = generate_fallback_lotteries()
        return _load_fallback_data()
    
    print(f"  ✓ Found {len(lottery_urls)} lottery URLs")
    
    # Parse each lottery page
    print("\n2. Parsing lottery pages...")
    lotteries = []
    for i, url in enumerate(lottery_urls[:20], 1):  # Limit to 20 for demo
        print(f"  Parsing {i}/{min(20, len(lottery_urls))}: {url}")
        lottery_data = parser.parse_lottery_page(url)
        if lottery_data:
            lotteries.append(lottery_data)
    
    print(f"\n  ✓ Successfully parsed {len(lotteries)} lotteries")
    
    # Load into database
    print("\n3. Loading lotteries into database...")
    loaded_count = 0
    for lottery in lotteries:
        try:
            result = Database.execute_query(
                """
                INSERT INTO lotteries (
                    name, slug, lottery_type, ticket_price, draw_frequency,
                    description, max_prize, url, is_active, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (slug) DO UPDATE SET
                    ticket_price = EXCLUDED.ticket_price,
                    draw_frequency = EXCLUDED.draw_frequency,
                    description = EXCLUDED.description,
                    max_prize = EXCLUDED.max_prize,
                    updated_at = EXCLUDED.updated_at
                RETURNING id
                """,
                (
                    lottery['name'],
                    lottery['slug'],
                    lottery['lottery_type'],
                    lottery['ticket_price'],
                    lottery['draw_frequency'],
                    lottery['description'],
                    lottery['max_prize'],
                    lottery['url'],
                    lottery['is_active'],
                    datetime.now(),
                    datetime.now()
                ),
                commit=True
            )
            loaded_count += 1
        except Exception as e:
            print(f"    ✗ Error loading {lottery['name']}: {e}")
    
    print(f"  ✓ Loaded {loaded_count} lotteries into database")
    return loaded_count


def load_draws():
    """Parse and load draw archive data"""
    print("\n" + "="*60)
    print("LOADING DRAW ARCHIVE DATA")
    print("="*60)
    
    parser = StolotoParser()
    
    # Get lottery IDs from database
    lotteries = Database.execute_query(
        "SELECT id, name, url FROM lotteries WHERE is_active = TRUE"
    )
    
    if not lotteries:
        print("  ⚠ No lotteries found in database. Load lotteries first.")
        return 0
    
    print(f"\n1. Found {len(lotteries)} lotteries to process")
    
    # Parse archive sitemap
    print("\n2. Fetching archive URLs from sitemap...")
    archive_urls = parser.parse_sitemap_archive()
    
    if not archive_urls:
        print("  ⚠ No archive URLs found. Skipping draw data.")
        return 0
    
    print(f"  ✓ Found {len(archive_urls)} archive URLs")
    
    # Parse draw archives (limit for demo)
    print("\n3. Parsing draw archives...")
    total_draws = 0
    for i, url in enumerate(archive_urls[:10], 1):  # Limit to 10 pages
        print(f"  Processing {i}/10: {url}")
        # Extract lottery ID from URL (simplified - would need real implementation)
        draws = parser.parse_draw_archive(url, lottery_id=1)
        if draws:
            # Load draws into database
            for draw in draws:
                try:
                    Database.execute_query(
                        """
                        INSERT INTO draws (
                            lottery_id, draw_number, draw_date, winning_numbers,
                            total_prize_fund, winners_count, created_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (lottery_id, draw_number) DO NOTHING
                        """,
                        (
                            draw['lottery_id'],
                            draw['draw_number'],
                            draw['draw_date'],
                            draw['winning_numbers'],
                            draw['total_prize_fund'],
                            draw['winners_count'],
                            datetime.now()
                        ),
                        commit=True
                    )
                    total_draws += 1
                except Exception as e:
                    print(f"    ✗ Error loading draw: {e}")
    
    print(f"\n  ✓ Loaded {total_draws} draws into database")
    return total_draws


def _load_fallback_data():
    """Load fallback lottery data for demo"""
    print("\nLoading fallback lottery data...")
    
    fallback_lotteries = [
        {
            'name': 'Русское лото',
            'slug': 'rusloto',
            'lottery_type': 'draw',
            'ticket_price': 100,
            'draw_frequency': '1 раз в неделю',
            'description': 'Самая популярная числовая лотерея в России',
            'max_prize': 500000000,
            'url': 'https://www.stoloto.ru/rusloto',
            'is_active': True
        },
        {
            'name': 'Жилищная лотерея',
            'slug': 'housing',
            'lottery_type': 'draw',
            'ticket_price': 100,
            'draw_frequency': '1 раз в неделю',
            'description': 'Лотерея с квартирами и крупными денежными призами',
            'max_prize': 30000000,
            'url': 'https://www.stoloto.ru/housing',
            'is_active': True
        },
        {
            'name': 'Рапидо',
            'slug': 'rapido',
            'lottery_type': 'draw',
            'ticket_price': 100,
            'draw_frequency': 'каждые 15 минут',
            'description': 'Быстрая лотерея с частыми розыгрышами',
            'max_prize': 5000000,
            'url': 'https://www.stoloto.ru/rapido',
            'is_active': True
        },
        {
            'name': '4 из 20',
            'slug': '4iz20',
            'lottery_type': 'draw',
            'ticket_price': 100,
            'draw_frequency': 'каждый день',
            'description': 'Ежедневная лотерея с высокой вероятностью выигрыша',
            'max_prize': 10000000,
            'url': 'https://www.stoloto.ru/4iz20',
            'is_active': True
        },
        {
            'name': '6 из 45',
            'slug': '6iz45',
            'lottery_type': 'draw',
            'ticket_price': 60,
            'draw_frequency': '2 раза в неделю',
            'description': 'Классическая числовая лотерея',
            'max_prize': 250000000,
            'url': 'https://www.stoloto.ru/6iz45',
            'is_active': True
        },
        {
            'name': 'Золотая подкова',
            'slug': 'gold_horseshoe',
            'lottery_type': 'instant',
            'ticket_price': 50,
            'draw_frequency': None,
            'description': 'Мгновенная лотерея',
            'max_prize': 1000000,
            'url': 'https://www.stoloto.ru/instant/gold_horseshoe',
            'is_active': True
        },
        {
            'name': 'Удача в придачу',
            'slug': 'luck_extra',
            'lottery_type': 'instant',
            'ticket_price': 100,
            'draw_frequency': None,
            'description': 'Мгновенная лотерея с крупными призами',
            'max_prize': 3000000,
            'url': 'https://www.stoloto.ru/instant/luck_extra',
            'is_active': True
        }
    ]
    
    loaded = 0
    for lottery in fallback_lotteries:
        try:
            Database.execute_query(
                """
                INSERT INTO lotteries (
                    name, slug, lottery_type, ticket_price, draw_frequency,
                    description, max_prize, url, is_active, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (slug) DO NOTHING
                """,
                (
                    lottery['name'],
                    lottery['slug'],
                    lottery['lottery_type'],
                    lottery['ticket_price'],
                    lottery['draw_frequency'],
                    lottery['description'],
                    lottery['max_prize'],
                    lottery['url'],
                    lottery['is_active'],
                    datetime.now(),
                    datetime.now()
                ),
                commit=True
            )
            loaded += 1
        except Exception as e:
            print(f"  ✗ Error loading {lottery['name']}: {e}")
    
    print(f"  ✓ Loaded {loaded} fallback lotteries")
    return loaded


def generate_fallback_lotteries():
    """Generate fallback lottery URLs"""
    return [
        'https://www.stoloto.ru/rusloto',
        'https://www.stoloto.ru/housing',
        'https://www.stoloto.ru/rapido',
        'https://www.stoloto.ru/4iz20',
        'https://www.stoloto.ru/6iz45'
    ]


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Load Stoloto lottery data into database')
    parser.add_argument('--lotteries', action='store_true', help='Load lottery data')
    parser.add_argument('--draws', action='store_true', help='Load draw archive data')
    parser.add_argument('--all', action='store_true', help='Load all data')
    
    args = parser.parse_args()
    
    # If no arguments, load all
    if not (args.lotteries or args.draws or args.all):
        args.all = True
    
    try:
        Database.initialize()
        
        if args.lotteries or args.all:
            load_lotteries()
        
        if args.draws or args.all:
            load_draws()
        
        print("\n" + "="*60)
        print("DATA LOADING COMPLETE!")
        print("="*60)
        
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        sys.exit(1)
    finally:
        Database.close_all()


if __name__ == '__main__':
    main()
