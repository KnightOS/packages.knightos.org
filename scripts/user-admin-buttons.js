var username = "";

function setup_user_admin(userprofile_username) {
    username = userprofile_username;

    document.getElementById("toggle-adminpanel-button").addEventListener('click', function(e) {
        $("#adminpanel").toggle();
        var button = document.getElementById("toggle-adminpanel-button");
        if ($('#adminpanel').is(':visible')) {
            button.innerHTML = 'Admin Panel <span class="glyphicon glyphicon-chevron-up"></span>';
        } else {
            button.innerHTML = 'Admin Panel <span class="glyphicon glyphicon-chevron-down"></span>';
        }
    }, false);
    document.getElementById("set-admin-button").addEventListener('click', function(e) {
        var xhr = new XMLHttpRequest();
        xhr.open('POST', '/api/v1/user/' + username + '/setadmin');
        xhr.onload = function() {
            window.location = window.location;
        };
        if(confirm("Make " + username + " an admin?"))
        {
            xhr.send();
        }
    }, false);
    document.getElementById("remove-admin-button").addEventListener('click', function(e) {
        var xhr = new XMLHttpRequest();
        xhr.open('POST', '/api/v1/user/' + username + '/removeadmin');
        xhr.onload = function() {
            window.location = window.location;
        };
        if(confirm("Remove " + username + " as admin?"))
        {
            xhr.send();
        }
    }, false);

    document.getElementById("confirm-user-button").addEventListener('click', function(e) {
        var xhr = new XMLHttpRequest();
        xhr.open('POST', '/api/v1/user/' + username + '/confirm/ADMIN');
        xhr.onload = function() {
            window.location = window.location;
        };
        if(confirm("Confirm " + username + "?"))
        {
            xhr.send();
        }
    }, false);
        document.getElementById("unconfirm-user-button").addEventListener('click', function(e) {
        var xhr = new XMLHttpRequest();
        xhr.open('POST', '/api/v1/user/' + username +'/unconfirm');
        xhr.onload = function() {
            window.location = window.location;
        };
        if(confirm("Unconfirm " + username + "?"))
        {
            xhr.send();
        }
    }, false);
}
