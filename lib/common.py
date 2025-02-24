from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    VectorSearchProfile,
    HnswParameters,
)

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores.azuresearch import AzureSearch


def create_schema(index_name:str)->list:
    # Define vector search configuration
    vector_search = VectorSearch(
        algorithms=[
            HnswParameters(
                name="my-hnsw-config",  # Add name for the algorithm configuration
                m=4,
                ef_construction=400,
                ef_search=500,
                metric="cosine"
            )
        ],
        profiles=[
            VectorSearchProfile(
                name="myHnswProfile",
                algorithm="hnsw",
                algorithm_configuration_name="my-hnsw-config"  # Reference the algorithm configuration name
            )
        ]
    )

    fields=[
            SearchField(
                name="id",
                type=SearchFieldDataType.String,
                key=True,
                hidden=False,
                filterable=True,
                sortable=True,
                facetable=False,
                searchable=True,
                analyzer_name="keyword"
            ),
            SearchField(
                name="content",
                type=SearchFieldDataType.String,
                hidden=False,
                filterable=False,
                sortable=False,
                facetable=False,
                searchable=True
            ),
            SearchField(
                name="title",
                type=SearchFieldDataType.String,
                hidden=False,
                filterable=False,
                sortable=False,
                facetable=False,
                searchable=True
            ),
            SearchField(
                name="metadata",
                type=SearchFieldDataType.String,
                hidden=False,
                filterable=False,
                sortable=False,
                facetable=False,
                searchable=True
            ),
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                hidden=False,
                filterable=False,
                sortable=False,
                facetable=False,
                searchable=True,
                vector_search_dimensions=3072,
                vector_search_profile_name="myHnswProfile"  # Reference to the profile name defined above
            )
    ]
    
    # Create SearchIndex with vector search configuration
    index = SearchIndex(
        name=index_name,
        fields=fields,
        vector_search=vector_search
    )
    
    return index

def create_embeddings(openai_api_key: str, openai_api_version:str, model:str) -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        openai_api_key=openai_api_key,
        openai_api_version=openai_api_version,
        model=model)

def create_search_index(azure_search_endpoint:str, azure_search_key:str, index_name:str, index:SearchIndex, embedding_function)-> AzureSearch:
    return AzureSearch(
        azure_search_endpoint=azure_search_endpoint,
        azure_search_key=azure_search_key,
        index_name=index_name,
        embedding_function=embedding_function,
        fields=index.fields
    )
