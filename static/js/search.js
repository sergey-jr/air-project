function search() {
    let checkbox = $("#delete_all");
    $("#search").hide();
    checkbox.hide();
    $("#reset").show();
    if (checkbox.prop("checked")) {
        search_delete();
    } else {
        let elem = $("#query");
        let query = elem.val();
        axios.get('/api/search', {
            params: {
                query: query
            }
        }).then(function (response) {
            let data = response.data;
            if (response.status === 200) {
                let docs = data.docs;
                if (docs != null) {
                    for (let i = 0; i < docs.length; i++) {
                        let doc = docs[i];
                        doc = [i + 1, `<a href='${doc[1].link}'>${doc[0]}</a>`,
                            `<img id="${doc[1].id}" class="icon-delete" src="static/icons/remove.png" alt="Delete">`];
                        docs[i] = doc;
                    }
                    let table = $('#results').DataTable({
                        data: docs,
                        searching: false,
                        pagingType: "full_numbers",
                        bLengthChange: false,
                        columns: [
                            {title: "#"},
                            {title: "File"},
                            {title: "", orderable: false}
                        ],
                    });
                    table.draw();
                    $('#results tbody').on('click', 'img.icon-delete', function () {
                        let file_id = $(this).attr('id');
                        let delete_fl = confirm("Are you sure to delete this file?");
                        console.log(delete_fl);
                        if (delete_fl) {
                            axios.post('/api/remove', {
                                file_id: file_id,
                            }).then(function () {
                                table.row($(this).parents('tr')).remove().draw();
                            }).catch(function (error) {
                                console.log(error);
                            });
                        }
                    });
                } else {
                    $("#files").html("Files for this query not found");
                }
            }
        }).catch(function (error) {
            console.log(error);
        });
    }
}

function search_delete() {
    let checkbox = $("#delete_all");
    let delete_fl = confirm("Are you sure to delete? " +
        "If you agree all files that refer to this query will be deleted permanently.");
    if (checkbox.prop("checked") && delete_fl) {
        let elem = $("#query");
        let query = elem.val();
        axios.get('/api/search_delete', {
            params: {
                query: query
            }
        }).then(function (response) {
            let data = response.data;
            if (response.status === 200) {
                let docs = data.docs;
                if (docs != null) {
                    for (let i = 0; i < docs.length; i++) {
                        let doc = docs[i];
                        doc = [i + 1, `${doc[0]}`];
                        docs[i] = doc;
                    }
                    $('#results').DataTable({
                        data: docs,
                        searching: false,
                        pagingType: "full_numbers",
                        bLengthChange: false,
                        columns: [
                            {title: "#"},
                            {title: "File"},
                        ],
                    });
                } else {
                    $("#files").html("Files for this query not found");
                }
            }
        });
    }
}

function reset() {
    location.reload();
}