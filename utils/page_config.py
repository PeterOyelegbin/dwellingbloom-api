from rest_framework.pagination import PageNumberPagination

class ListPagination(PageNumberPagination):
    page_size = 20                       # default results per page
    page_size_query_param = 'page_size'  # allow client to override, e.g. ?page_size=50
    max_page_size = 100                  # hard ceiling
