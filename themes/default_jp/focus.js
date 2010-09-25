<!--//--><![CDATA[//><!--

sfFocus = function() {
	var sfEls = document.getElementsByTagName("INPUT");
	for (var i=0; i<sfEls.length; i++) {
		sfEls[i].onfocus=function() {
			this.className+=" sffocus";
		}
		sfEls[i].onblur=function() {
			this.className=this.className.replace(new RegExp(" sffocus\\b"), "");
		}
	}
}
if (window.attachEvent) window.attachEvent("onload", sfFocus);

//--><!]]>