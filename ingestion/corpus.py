"""WHICH papers we download: the corpus settings, in one single place.

Rule: among the papers that match the filter below, we keep the MAX_PAPERS
most-cited ones (sorted by number of citations, highest first).
So the corpus size is always reasonable, whatever the number of matching papers
(the filter alone matches hundreds of thousands).

Every script (the exploration now, the full download later) reads these
settings, so they always agree.
"""

#Corpus settings
#can be modified for desired papers
FROM_YEAR = 2018
TO_YEAR = 2025
FIELD_ID = 17 #17 = "Computer Science"!! , not really necessary but great for scpecification!
WORK_TYPE = "article"
LANGUAGE = "en" 

MAX_PAPERS = 25000 
SORT = "cited_by_count:desc"  #most-cited first!


#create the filter using these params 
def build_filter() -> str:
    return ",".join([
        "has_abstract:true",#abstract for embedding 
        f"type:{WORK_TYPE}",
        f"language:{LANGUAGE}",
        f"publication_year:>{FROM_YEAR - 1}",   #[2018...
        f"publication_year:<{TO_YEAR + 1}",     # ...2025]
        f"primary_topic.field.id:{FIELD_ID}",   #Computer Science FIELD
    ])
