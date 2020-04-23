axios.get('/api/test', {
    params: {}
}).then(function (response) {
    let data = response.data;
    if (response.status === 200) {
        let files = data.files;
        for (let i = 0; i < files.length; i++) {
            let file = files[i];
            file = [i + 1, `<a href='${file.webViewLink}'>${file.name}</a>`];
            files[i] = file;
        }
        $('#results').DataTable({
            data: files,
            searching: false,
            pagingType: "full_numbers",
            columns: [
                {title: "#"},
                {title: "File"},
            ],
        });
    }
});