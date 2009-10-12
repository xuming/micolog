 tinyMCE.init({
        // General options
        mode : "exact",    <!-- 只替换指定的目标 -->
        elements: "content",  <!-- 替换id为content的textarea为tinymce的编辑器 -->
        theme : "advanced",
        skin:"wp_theme",
        language : "zh",
        plugins : "wordpress,safari,pagebreak,save,advhr,advimage,advlink,emotions, inlinepopups,media,directionality,visualchars,nonbreaking,emotions,fullscreen",
        // Theme options
        theme_advanced_buttons1:"bold,italic,strikethrough,|,bullist,numlist,blockquote,|,justifyleft,justifycenter,justifyright,|,link,unlink,image,wp_more,|,fullscreen,wp_adv",
        theme_advanced_buttons2:"formatselect,underline,justifyfull,forecolor,|,pastetext,pasteword,removeformat,|,media,charmap,emotions,|,outdent,indent,|,undo,redo",
        theme_advanced_buttons3:"",
        theme_advanced_buttons4:"",
        //theme_advanced_buttons1 : "save,newdocument,|,forecolor,backcolor, formatselect,fontselect,fontsizeselect,bold,italic,underline,strikethrough,| ,justifyleft,justifycenter,justifyright,justifyfull",
        //theme_advanced_buttons2 : "bullist,numlist,|,outdent,indent,blockquote,pre,|, undo,redo,|,link,unlink,anchor,image,cleanup,help,code",
        //theme_advanced_buttons3 : "hr,removeformat,visualaid,|,sub,sup,|,charmap,emotions,iespell, media,advhr,|,ltr,rtl,|,highlight,|,visualchars,nonbreaking,pagebreak",
        theme_advanced_toolbar_location : "top",
        theme_advanced_toolbar_align : "left",
        theme_advanced_statusbar_location : "bottom",
        theme_advanced_resizing : true,
        // Example content CSS (should be your site CSS)
        content_css : "/tinymce/wordpress.css",
    
        // Drop lists for link/image/media/template dialogs
        template_external_list_url : "lists/template_list.js",




        external_link_list_url : "lists/link_list.js",
        external_image_list_url : "lists/image_list.js",
        media_external_list_url : "lists/media_list.js"
    });