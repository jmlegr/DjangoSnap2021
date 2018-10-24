
var urls = {
        'visualise':"sessions/visualise/",
        'reperes':"sessions/reperes/",
}

var xsend = function (url, csrf_token, data, method = "GET") {
    return fetch(url, {
            method: method, // *GET, POST, PUT, DELETE, etc.
            mode: "cors", // no-cors, cors, *same-origin
            cache: "no-cache", // *default, no-cache, reload, force-cache, only-if-cached
            credentials: "same-origin", // include, same-origin, *omit
            headers: {
                "Content-Type": "application/json; charset=utf-8",
                'X-CSRFToken': csrf_token,
                // "Content-Type": "application/x-www-form-urlencoded",
            },
            redirect: "follow", // manual, *follow, error
            referrer: "no-referrer", // no-referrer, *client
            body: JSON.stringify(data), // body data type must match "Content-Type" header
        })
        .then(response => response.json())
        //.then(response => console.log('Success:', response,JSON.stringify(response)))
        .catch(error => console.error('Erroddr:', error));; // parses response to JSON
}

export {
    urls,
    xsend
}
