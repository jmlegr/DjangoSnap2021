
var urls = {
        'visualise':"sessions/visualise/",
        'reperes':"sessions/reperes/",
        'programmes':'toliste/'
}

var xsend = function (url, csrf_token, data, method = "GET") {
    let options={
            method: method, // *GET, POST, PUT, DELETE, etc.
            mode: "cors", // no-cors, cors, *same-origin
            cache: "no-cache", // *default, no-cache, reload, force-cache, only-if-cached
            credentials: "same-origin", // include, same-origin, *omit
            headers: {
                "Content-Type": "application/json; charset=utf-8",
                'X-CSRFToken': csrf_token,
                'X-Requested-With':'XMLHttpRequest'
                // "Content-Type": "application/x-www-form-urlencoded",
            },
            redirect: "follow", // manual, *follow, error
            referrer: "no-referrer", // no-referrer, *client            
        }
    if (method=="POST") options.body= JSON.stringify(data) // body data type must match "Content-Type" header
    return fetch(url, options)
        .then(response => response.json())
        //.then(response => console.log('Success:', response,JSON.stringify(response)))
        .catch(error => console.error('Erroddr:', error));; // parses response to JSON
}
var ysend = function (url, csrf_token, data, method = "GET") {
    let options={
            method: method, // *GET, POST, PUT, DELETE, etc.
            mode: "cors", // no-cors, cors, *same-origin
            cache: "no-cache", // *default, no-cache, reload, force-cache, only-if-cached
            credentials: "same-origin", // include, same-origin, *omit
            headers: {
                "Content-Type": "text/html ; charset=utf-8",
                'X-CSRFToken': csrf_token,
                // "Content-Type": "application/x-www-form-urlencoded",
            },
            redirect: "follow", // manual, *follow, error
            referrer: "no-referrer", // no-referrer, *client            
        }
    if (method=="POST") options.body= data // body data type must match "Content-Type" header
    return fetch(url, options)
        .then(response => response.text())
        //.then(response => console.log('Success:', response,JSON.stringify(response)))
        .catch(error => console.error('Erroddr:', error));; // parses response to JSON
}

export {
    urls,
    xsend, ysend
}
