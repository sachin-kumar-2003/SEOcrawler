from pydantic import BaseModel, Field,AnyHttpUrl
from typing import  List,Annotated

class UrlForCrawl(BaseModel):
    url:Annotated[str,Field(...,description="Enter the url for finding broken links")]

# class UrlLink(BaseModel):
#     url:Annotated[AnyHttpUrl,Field(description="Broken link found in the website")]

# class CrawlResponse(BaseModel):
#     total= int
#     brokenLinksList= Annotated(List[UrlLink],Field(description="List of broken links"))
#     correctLinkList=Annotated[List[UrlLink],Field(description="List of perfect links found")]
    
