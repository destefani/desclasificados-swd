#!/usr/bin/env python3
"""
Quick test script for Claude RAG integration.

This script tests:
1. Anthropic API key is configured
2. Claude can be imported and initialized
3. Vector database is accessible
4. A simple query works end-to-end with Claude

Usage:
    python test_claude_integration.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_api_key():
    """Test that ANTHROPIC_API_KEY is configured."""
    print("=" * 80)
    print("TEST 1: API Key Configuration")
    print("=" * 80)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ FAIL: ANTHROPIC_API_KEY not found in environment")
        print("\nTo fix:")
        print("1. Get your API key from: https://console.anthropic.com/settings/keys")
        print("2. Add to .env file:")
        print("   ANTHROPIC_API_KEY=your_key_here")
        print("3. Restart your terminal or reload .env")
        return False

    print(f"✅ PASS: ANTHROPIC_API_KEY is set (length: {len(api_key)})")
    return True


def test_imports():
    """Test that required modules can be imported."""
    print("\n" + "=" * 80)
    print("TEST 2: Module Imports")
    print("=" * 80)

    try:
        from anthropic import Anthropic
        print("✅ PASS: anthropic module imported")
    except ImportError as e:
        print(f"❌ FAIL: Could not import anthropic: {e}")
        print("\nTo fix: uv add anthropic")
        return False

    try:
        from app.rag.qa_pipeline_claude import ask_question_claude
        print("✅ PASS: Claude QA pipeline module imported")
    except ImportError as e:
        print(f"❌ FAIL: Could not import Claude QA pipeline: {e}")
        return False

    try:
        from app.rag.vector_store import init_vector_store
        print("✅ PASS: Vector store module imported")
    except ImportError as e:
        print(f"❌ FAIL: Could not import vector store: {e}")
        return False

    return True


def test_anthropic_client():
    """Test that Anthropic client can be initialized."""
    print("\n" + "=" * 80)
    print("TEST 3: Anthropic Client Initialization")
    print("=" * 80)

    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        print("✅ PASS: Anthropic client initialized")
        return True
    except Exception as e:
        print(f"❌ FAIL: Could not initialize Anthropic client: {e}")
        return False


def test_vector_database():
    """Test that vector database is accessible."""
    print("\n" + "=" * 80)
    print("TEST 4: Vector Database")
    print("=" * 80)

    try:
        from app.rag.vector_store import init_vector_store
        vector_store = init_vector_store()
        count = vector_store.count()

        if count == 0:
            print("❌ FAIL: Vector database is empty")
            print("\nTo fix:")
            print("   uv run python -m app.rag.cli build")
            return False

        print(f"✅ PASS: Vector database loaded ({count:,} chunks)")
        return True
    except Exception as e:
        print(f"❌ FAIL: Could not access vector database: {e}")
        return False


def test_simple_query():
    """Test a simple end-to-end query with Claude."""
    print("\n" + "=" * 80)
    print("TEST 5: Simple Query with Claude")
    print("=" * 80)

    test_question = "What did the CIA know about Operation Condor?"
    print(f"Question: {test_question}")
    print("\nGenerating answer with Claude 3.5 Haiku...")

    try:
        from app.rag.vector_store import init_vector_store
        from app.rag.qa_pipeline_claude import ask_question_claude

        vector_store = init_vector_store()

        result = ask_question_claude(
            vector_store=vector_store,
            question=test_question,
            top_k=3,  # Use fewer docs for faster test
            model="claude-3-5-haiku-20241022",
        )

        print("\n" + "-" * 80)
        print("ANSWER:")
        print("-" * 80)
        print(result["answer"][:500] + "..." if len(result["answer"]) > 500 else result["answer"])

        print("\n" + "-" * 80)
        print(f"SOURCES: {result['num_sources']} documents")
        print("-" * 80)
        for i, source in enumerate(result["sources"], 1):
            print(f"{i}. Doc {source['document_id']} ({source['date']}) - Relevance: {source['relevance_score']:.2%}")

        print("\n✅ PASS: Query completed successfully with Claude!")
        return True

    except Exception as e:
        print(f"\n❌ FAIL: Query failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_model_comparison():
    """Test both OpenAI and Claude for comparison."""
    print("\n" + "=" * 80)
    print("TEST 6: Model Comparison (Optional)")
    print("=" * 80)

    test_question = "What was the CIA's relationship with Manuel Contreras?"
    print(f"Question: {test_question}\n")

    try:
        from app.rag.vector_store import init_vector_store
        from app.rag.qa_pipeline_claude import ask_question_claude
        from app.rag.qa_pipeline import ask_question

        vector_store = init_vector_store()

        # Test with Claude
        print("Testing with Claude 3.5 Haiku...")
        claude_result = ask_question_claude(
            vector_store=vector_store,
            question=test_question,
            top_k=3,
            model="claude-3-5-haiku-20241022",
        )
        print(f"✅ Claude: {len(claude_result['answer'])} chars, {claude_result['num_sources']} sources")

        # Test with OpenAI
        print("Testing with OpenAI GPT-4o-mini...")
        openai_result = ask_question(
            vector_store=vector_store,
            question=test_question,
            top_k=3,
            model="gpt-4o-mini",
        )
        print(f"✅ OpenAI: {len(openai_result['answer'])} chars, {openai_result['num_sources']} sources")

        print("\n✅ PASS: Both models working!")
        print("\nYou can now compare the quality of answers from both models.")
        return True

    except Exception as e:
        print(f"⚠️  SKIP: Could not run comparison: {e}")
        return True  # Don't fail the test suite for this


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("CLAUDE RAG INTEGRATION TEST SUITE")
    print("=" * 80)

    tests = [
        ("API Key", test_api_key),
        ("Imports", test_imports),
        ("Anthropic Client", test_anthropic_client),
        ("Vector Database", test_vector_database),
        ("Simple Query", test_simple_query),
        ("Model Comparison", test_model_comparison),
    ]

    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))

            # If a critical test fails, stop
            if not passed and name in ["API Key", "Imports", "Anthropic Client", "Vector Database"]:
                print(f"\n❌ Critical test '{name}' failed. Stopping test suite.")
                break

        except KeyboardInterrupt:
            print("\n\nTest interrupted by user")
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ Test '{name}' raised exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    passed = sum(1 for _, p in results if p)
    total = len(results)

    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {name}")

    print("\n" + "=" * 80)
    print(f"Result: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! Claude integration is working correctly.")
        print("\nNext steps:")
        print("1. Try: uv run python -m app.rag.cli query 'Your question here'")
        print("2. Try: uv run python -m app.rag.cli interactive")
        print("3. Compare with OpenAI: Add --llm openai flag")
        return 0
    else:
        print(f"\n⚠️  Some tests failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
