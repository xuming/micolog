sfHover = function() {
	if (!document.getElementsByTagName) return false;
	var nav = document.getElementById("nav");
	if (!nav) return false;

	var sfEls = nav.getElementsByTagName("li");

	for (var i=0; i<sfEls.length; i++) {
		sfEls[i].onmouseover = function() {
			this.className += " sfhover";
		};
		sfEls[i].onmouseout = function() {
			this.className = this.className.replace(new RegExp(" sfhover\\b"), "");
		};
	}
};

if (window.attachEvent) {
	window.attachEvent("onload", sfHover);
}