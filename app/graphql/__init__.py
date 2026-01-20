"""
GraphQL Package

This package provides GraphQL API functionality using Strawberry GraphQL.
It offers an alternative to the REST API for flexible data fetching.

Features:
- Type-safe schema matching SQLAlchemy models
- Query resolvers for all entities
- Mutation resolvers for CRUD operations
- Authentication via JWT in context
- Pagination support
- Relationship resolution

Usage:
    The GraphQL endpoint is available at /graphql with an
    interactive GraphiQL playground for development.

Example Query:
    query {
        books(page: 1, perPage: 10) {
            items {
                id
                title
                authors { name }
            }
            total
        }
    }
"""

import strawberry
from strawberry.fastapi import GraphQLRouter

from app.graphql.context import get_context
from app.graphql.mutations import Mutation
from app.graphql.queries import Query

# Create the GraphQL schema
schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
)


def create_graphql_router() -> GraphQLRouter:
    """
    Create the GraphQL router for FastAPI.

    Returns:
        GraphQLRouter configured with schema and context
    """
    return GraphQLRouter(
        schema,
        context_getter=get_context,
        # Use Apollo Sandbox for better browser compatibility
        # Options: "graphiql", "apollo-sandbox", or None to disable
        graphql_ide="apollo-sandbox",
    )


__all__ = ["schema", "create_graphql_router"]
