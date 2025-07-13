from pydantic import BaseModel, Field,AnyHttpUrl
from typing import  List,Annotated

class UrlForCrawl(BaseModel):
    url:Annotated[AnyHttpUrl,Field(...,description="Enter the url for finding broken links")]

class UrlLink(BaseModel):
    url:Annotated[AnyHttpUrl,Field(description="Broken link found in the website")]

class BrokenLinksResponse(BaseModel):
    total=Annotated(int,Field(description="Total broken links found"))
    brokenLinks= Annotated(List[UrlLink],Field(description="List of broken links"))
    
class CorrectLinkResponse(BaseModel):
    url:Annotated[AnyHttpUrl,Field(description="Correct link found in the website")]
    correctLink=Annotated[List[UrlLink],Field(description="List of perfect links found")]

