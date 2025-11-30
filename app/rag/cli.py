"""Command-line interface for the RAG system."""

import argparse
import sys
from pathlib import Path
from typing import Optional, List
from app.rag.embeddings import (
    load_all_data,
    create_document_chunks,
    generate_embeddings,
)
from app.rag.vector_store import init_vector_store, build_index
from app.rag.qa_pipeline import ask_question
from app.rag.qa_pipeline_claude import ask_question_claude
from app.rag.config import VECTOR_DB_DIR, CLAUDE_MODEL, LLM_MODEL


def build_command(args):
    """Build the vector database index."""
    print("=" * 80)
    print("Building RAG Index")
    print("=" * 80)

    # Load transcripts
    print("\n1. Loading transcripts...")
    transcripts = load_all_data()

    if not transcripts:
        print("Error: No transcripts found!")
        sys.exit(1)

    print(f"Loaded {len(transcripts)} transcripts")

    # Create chunks
    print("\n2. Creating document chunks...")
    chunks = create_document_chunks(transcripts)
    print(f"Created {len(chunks)} chunks")

    # Generate embeddings
    print("\n3. Generating embeddings...")
    chunks_with_embeddings = generate_embeddings(chunks)
    print(f"Generated embeddings for {len(chunks_with_embeddings)} chunks")

    # Build index
    print("\n4. Building vector database...")
    vector_store = build_index(chunks_with_embeddings, reset=args.reset)

    print("\n" + "=" * 80)
    print(f"Index built successfully!")
    print(f"Total chunks indexed: {vector_store.count()}")
    print(f"Database location: {VECTOR_DB_DIR}")
    print("=" * 80)


def query_command(args):
    """Query the RAG system."""
    # Initialize vector store
    vector_store = init_vector_store()

    if vector_store.count() == 0:
        print("Error: Vector database is empty. Please run 'build' first.")
        sys.exit(1)

    print(f"Database loaded: {vector_store.count()} chunks")
    print(f"LLM: {args.llm}")
    if args.model:
        print(f"Model: {args.model}")
    print("=" * 80)

    # Parse optional filters
    date_range = None
    if args.start_date or args.end_date:
        date_range = (args.start_date, args.end_date)

    keywords = None
    if args.keywords:
        keywords = [k.strip() for k in args.keywords.split(",")]

    # Determine which model to use
    if args.llm == "claude":
        model = args.model or CLAUDE_MODEL
        result = ask_question_claude(
            vector_store=vector_store,
            question=args.query,
            top_k=args.top_k,
            date_range=date_range,
            keywords=keywords,
            model=model,
        )
    else:  # openai
        model = args.model or LLM_MODEL
        result = ask_question(
            vector_store=vector_store,
            question=args.query,
            top_k=args.top_k,
            date_range=date_range,
            keywords=keywords,
            model=model,
        )

    # Display results
    print("\n" + "=" * 80)
    print("ANSWER:")
    print("=" * 80)
    print(result["answer"])

    print("\n" + "=" * 80)
    print(f"SOURCES ({result['num_sources']} documents):")
    print("=" * 80)

    for i, source in enumerate(result["sources"], 1):
        print(f"\n{i}. Document {source['document_id']}")
        print(f"   Date: {source['date']}")
        print(f"   Type: {source['type']}")
        print(f"   Classification: {source['classification']}")
        print(f"   Author: {source['author']}")
        print(f"   Relevance: {source['relevance_score']:.2%}")
        print(f"   Excerpt: {source['excerpt']}")

    print("\n" + "=" * 80)


def interactive_command(args):
    """Interactive query mode."""
    # Initialize vector store
    vector_store = init_vector_store()

    if vector_store.count() == 0:
        print("Error: Vector database is empty. Please run 'build' first.")
        sys.exit(1)

    print("=" * 80)
    print("RAG Interactive Mode")
    print("=" * 80)
    print(f"Database loaded: {vector_store.count()} chunks")
    print(f"LLM: {args.llm}")
    if args.model:
        print(f"Model: {args.model}")
    print("\nType 'exit' or 'quit' to exit")
    print("Type 'help' for available commands")
    print("=" * 80)

    while True:
        try:
            # Get user input
            print("\n")
            question = input("Question: ").strip()

            if not question:
                continue

            if question.lower() in ["exit", "quit", "q"]:
                print("Goodbye!")
                break

            if question.lower() == "help":
                print("\nAvailable commands:")
                print("  - Type any question to query the documents")
                print("  - 'exit', 'quit', 'q' - Exit interactive mode")
                print("  - 'help' - Show this help message")
                continue

            # Query the system
            if args.llm == "claude":
                model = args.model or CLAUDE_MODEL
                result = ask_question_claude(
                    vector_store=vector_store,
                    question=question,
                    top_k=5,
                    model=model,
                )
            else:  # openai
                model = args.model or LLM_MODEL
                result = ask_question(
                    vector_store=vector_store,
                    question=question,
                    top_k=5,
                    model=model,
                )

            # Display answer
            print("\n" + "-" * 80)
            print("ANSWER:")
            print("-" * 80)
            print(result["answer"])

            # Display sources
            print(f"\nSources: {result['num_sources']} documents")
            for i, source in enumerate(result["sources"], 1):
                print(f"  {i}. Doc {source['document_id']} ({source['date']}) - {source['type']}")

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")
            continue


def stats_command(args):
    """Show database statistics."""
    vector_store = init_vector_store()

    print("=" * 80)
    print("RAG Database Statistics")
    print("=" * 80)
    print(f"Total chunks: {vector_store.count()}")
    print(f"Database location: {VECTOR_DB_DIR}")
    print("=" * 80)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="RAG system for declassified CIA documents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Build command
    build_parser = subparsers.add_parser("build", help="Build the vector database index")
    build_parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset the database before building",
    )

    # Query command
    query_parser = subparsers.add_parser("query", help="Query the RAG system")
    query_parser.add_argument("query", type=str, help="Question to ask")
    query_parser.add_argument(
        "--llm",
        type=str,
        choices=["openai", "claude"],
        default="openai",
        help="LLM to use for answer generation (default: openai)",
    )
    query_parser.add_argument(
        "--model",
        type=str,
        help="Specific model to use (overrides default for selected LLM)",
    )
    query_parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of documents to retrieve (default: 5)",
    )
    query_parser.add_argument(
        "--start-date",
        type=str,
        help="Start date filter (YYYY-MM-DD)",
    )
    query_parser.add_argument(
        "--end-date",
        type=str,
        help="End date filter (YYYY-MM-DD)",
    )
    query_parser.add_argument(
        "--keywords",
        type=str,
        help="Comma-separated keywords to filter by",
    )

    # Interactive command
    interactive_parser = subparsers.add_parser(
        "interactive",
        help="Interactive query mode",
    )
    interactive_parser.add_argument(
        "--llm",
        type=str,
        choices=["openai", "claude"],
        default="openai",
        help="LLM to use for answer generation (default: openai)",
    )
    interactive_parser.add_argument(
        "--model",
        type=str,
        help="Specific model to use (overrides default for selected LLM)",
    )

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show database statistics")

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute command
    if args.command == "build":
        build_command(args)
    elif args.command == "query":
        query_command(args)
    elif args.command == "interactive":
        interactive_command(args)
    elif args.command == "stats":
        stats_command(args)


if __name__ == "__main__":
    main()
