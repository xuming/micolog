function showPageLink(sUrl,iPage,iCount,sAnchor){
var i;
i=Math.max(1,iPage-1);
if(iPage==1){
document.write("<span style='color:#7D7D7D'>Home</span> ");
}
else{
document.write("<a href=\"" + sUrl + sAnchor + "1\" title='Home'>Home</a> ");
document.write("<a href=\"" + sUrl + i + sAnchor + "\" title='Prev(Page " + i + ")'><</a> ");
}
if(iPage>5) document.write("<span>...</span> ");
for(i=Math.max(1,iPage-4);i<iPage;i++){
document.write("<a href=\""+sUrl + i + sAnchor + "\" title='Page " + i + "'>" + i + "</a> ");
}
document.write("<span style='color:#cc0000'>" + iPage + "</span> ");
for(i=iPage+1;i<=Math.min(iCount,iPage+4);i++){
document.write("<a href=\""+sUrl + i + sAnchor + "\" title='Page " + i + "'>" + i + "</a> ");
}
i=Math.min(iCount,iPage+1);
if(iCount>iPage+4) document.write("<span>...</span> ");
if(iPage==iCount){
document.write("<span style='color:#7D7D7D'> Last </span> ");
}
else{
document.write("<a href=\"" + sUrl + i + sAnchor + "\" title='Next(Page " + i + ")'>></a> ");
document.write("<a href=\"" + sUrl + iCount + sAnchor + "\" title='Last(Page " + iCount + ")'>Last</a> ");
}
}