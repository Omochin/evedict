$(document).ready(function () {
    if (!window.console) window.console = {};
    if (!window.console.log) window.console.log = function () { };

    $('#search-query').keypress(function (e) {
        v = $('#search-query').val();
        if (e.which == 13 && v) {
            url = '/' + $('#search-lcid').val() + '/type/' + v;
            return updater.link_to(url);
        }
    });
    
    updater.start();
});

var updater = {
    socket: null,

    start: function () {
        var url = 'ws://' + location.host + '/update';
        updater.socket = new WebSocket(url);
        updater.socket.onmessage = function (event) {
            updater.updatePage(JSON.parse(event.data));
        }
        updater.socket.onclose = function (event) {
            setTimeout("updater.start()", 1000);
        }
    },

    updatePage: function (message) {		
        $('#search-query').val(message.search_word);
        
        if (message.url) {
            window.location.href = message.url;
        }
    },

    link_to: function (url) {
        if (updater.socket) {
            updater.socket.send(JSON.stringify({'url': url}));            
            return false;
        } else {
            return true;
        }
    },
};
