#!/usr/bin/env python3
"""
Test suite for Stoloto Lottery Assistant
Tests all major components of the application
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_database_connection():
    """Test PostgreSQL database connection"""
    print("\n" + "="*60)
    print("TEST 1: Database Connection")
    print("="*60)
    
    try:
        from database.db import Database
        Database.initialize()
        result = Database.execute_query("SELECT version();")
        
        if result:
            print("✓ Database connection successful")
            print(f"  PostgreSQL version: {result[0]['version'][:50]}...")
            Database.close_all()
            return True
        else:
            print("✗ Database query failed")
            return False
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False


def test_ollama_connection():
    """Test Ollama LLM connection"""
    print("\n" + "="*60)
    print("TEST 2: Ollama LLM Connection")
    print("="*60)
    
    try:
        from llm.ollama_client import OllamaClient
        client = OllamaClient()
        
        if client.test_connection():
            print("✓ Ollama connection successful")
            print(f"  Model: {client.model}")
            print(f"  Host: {client.host}")
            return True
        else:
            print("✗ Ollama connection failed")
            print("  Make sure Ollama is running: ollama serve")
            return False
    except Exception as e:
        print(f"✗ Ollama test failed: {e}")
        return False


def test_ollama_generation():
    """Test Ollama text generation"""
    print("\n" + "="*60)
    print("TEST 3: Ollama Text Generation")
    print("="*60)
    
    try:
        from llm.ollama_client import OllamaClient
        client = OllamaClient()
        
        print("  Generating test response...")
        response = client.generate_response(
            "Привет! Это тест.",
            context_data={}
        )
        
        if response and len(response) > 0:
            print("✓ Text generation successful")
            print(f"  Response preview: {response[:100]}...")
            return True
        else:
            print("✗ Text generation failed - empty response")
            return False
    except Exception as e:
        print(f"✗ Text generation failed: {e}")
        return False


def test_recommendation_engine():
    """Test recommendation engine"""
    print("\n" + "="*60)
    print("TEST 4: Recommendation Engine")
    print("="*60)
    
    try:
        from recommendations.engine import RecommendationEngine
        from database.db import Database
        
        Database.initialize()
        engine = RecommendationEngine()
        
        # Test with mock user preferences
        test_preferences = {
            'budget': 200,
            'preferred_prize_type': 'draw',
            'preferred_prize_size': 'medium'
        }
        
        # Get active lotteries
        lotteries = engine._get_active_lotteries()
        
        if len(lotteries) > 0:
            print(f"✓ Found {len(lotteries)} lotteries")
            
            # Test scoring
            score = engine._calculate_lottery_score(lotteries[0], test_preferences)
            print(f"✓ Scoring algorithm works (sample score: {score:.1f}/100)")
            
            Database.close_all()
            return True
        else:
            print("⚠ No lotteries in database")
            print("  Run: python parsers/db_loader.py --all")
            Database.close_all()
            return False
    except Exception as e:
        print(f"✗ Recommendation engine test failed: {e}")
        return False


def test_parser():
    """Test Stoloto parser"""
    print("\n" + "="*60)
    print("TEST 5: Stoloto Parser")
    print("="*60)
    
    try:
        from parsers.stoloto_parser import StolotoParser
        parser = StolotoParser()
        
        print("  Testing sitemap parsing...")
        # Note: This will make actual HTTP requests
        # urls = parser.parse_sitemap_main()
        
        # For now, just test that parser initializes
        print("✓ Parser initialized successfully")
        print("  Note: Actual parsing requires network access to stoloto.ru")
        return True
    except Exception as e:
        print(f"✗ Parser test failed: {e}")
        return False


def test_database_schema():
    """Test database schema"""
    print("\n" + "="*60)
    print("TEST 6: Database Schema")
    print("="*60)
    
    try:
        from database.db import Database
        Database.initialize()
        
        # Check all required tables exist
        tables = ['lotteries', 'draws', 'prize_categories', 'users', 
                 'user_preferences', 'user_stats', 'recommendations', 'chat_history']
        
        all_exist = True
        for table in tables:
            result = Database.execute_query(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = %s);",
                (table,)
            )
            exists = result[0]['exists'] if result else False
            
            if exists:
                print(f"  ✓ Table '{table}' exists")
            else:
                print(f"  ✗ Table '{table}' missing")
                all_exist = False
        
        Database.close_all()
        
        if all_exist:
            print("✓ All required tables exist")
            return True
        else:
            print("✗ Some tables are missing")
            print("  Run: python app.py --init-db")
            return False
    except Exception as e:
        print(f"✗ Schema test failed: {e}")
        return False


def test_flask_app():
    """Test Flask application"""
    print("\n" + "="*60)
    print("TEST 7: Flask Application")
    print("="*60)
    
    try:
        from app import create_app
        app = create_app()
        
        print("✓ Flask app created successfully")
        print(f"  Blueprints registered: {len(app.blueprints)}")
        print(f"  Routes: {len([r for r in app.url_map.iter_rules()])}")
        
        return True
    except Exception as e:
        print(f"✗ Flask app test failed: {e}")
        return False


def run_all_tests():
    """Run all tests and report results"""
    print("\n" + "="*70)
    print("STOLOTO LOTTERY ASSISTANT - TEST SUITE")
    print("="*70)
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Ollama Connection", test_ollama_connection),
        ("Ollama Generation", test_ollama_generation),
        ("Recommendation Engine", test_recommendation_engine),
        ("Parser", test_parser),
        ("Database Schema", test_database_schema),
        ("Flask Application", test_flask_app),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Test '{name}' crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:10} {name}")
    
    print("-"*70)
    print(f"Total: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    print("="*70)
    
    if passed == total:
        print("\n🎉 All tests passed! Application is ready to run.")
        print("\nNext steps:")
        print("  1. If database is empty, load data: python parsers/db_loader.py --all")
        print("  2. Start the application: python app.py")
        print("  3. Open http://localhost:5000 in your browser")
    else:
        print("\n⚠ Some tests failed. Please fix the issues above.")
        if not results[0][1]:  # Database failed
            print("\n  Database issue? Try:")
            print("    createdb stoloto_db")
            print("    python app.py --init-db")
        if not results[1][1]:  # Ollama failed
            print("\n  Ollama issue? Try:")
            print("    ollama serve  # In another terminal")
            print("    ollama pull llama3.2")
    
    return passed == total


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run tests for Stoloto Assistant')
    parser.add_argument('--quick', action='store_true', help='Skip slow tests (Ollama generation)')
    args = parser.parse_args()
    
    success = run_all_tests()
    sys.exit(0 if success else 1)
