	/*
	  Function determines whether all of the proper form items contain content before signature file is uploaded
	*/
	function uploadPreReqs(){
		uploadButton = document.getElementById("file-load-button");
		if (document.getElementById("firstName").value &&
			document.getElementById("firstName").value != '' &&
			document.getElementById("lastName").value &&
			document.getElementById("lastName").value != '' &&
			document.getElementById("email").value &&
			document.getElementById("email").value != '') {
			uploadButton.disabled = false;
		}
		else{
			uploadButton.disabled = true;
		}
	}
	
	function deleteTempFile(filename){
		const xhr = new XMLHttpRequest();
		xhr.open('GET', "/delete_s3/?file_name="+filename);
		xhr.send();
	}
	
    /*
      Function to carry out the actual POST request to S3 using the signed request from the Python app.
	  Source: https://devcenter.heroku.com/articles/s3-upload-python
    */
    function uploadFile(file, s3Data, url){
      const xhr = new XMLHttpRequest();
      xhr.open('POST', s3Data.url);
      xhr.setRequestHeader('x-amz-acl', 'public-read', 'Access-Control-Allow-Origin');
      const postData = new FormData();
      for(key in s3Data.fields){
        postData.append(key, s3Data.fields[key]);
      }
      postData.append('file', file);
      xhr.onreadystatechange = () => {
        if(xhr.readyState === 4){
          if(xhr.status === 200 || xhr.status === 204){
            document.getElementById('sig-url').value = url;
          }
          else{
            //alert('Could not upload file.');
          }
        }
      };
      xhr.send(postData);
    }
	
    /*
      Function to carry out the actual POST request to S3 using the signed request from the Python app.
	  This function uploads a temporary signature file to the database to keep the browser cache from
	  loading an older version of the signature file
	  Source: https://devcenter.heroku.com/articles/s3-upload-python
    */
    function uploadTempFile(file, s3Data, url, filename){
      const xhr = new XMLHttpRequest();
      xhr.open('POST', s3Data.url);
      xhr.setRequestHeader('x-amz-acl', 'public-read', 'Access-Control-Allow-Origin');
      const postData = new FormData();
      for(key in s3Data.fields){
        postData.append(key, s3Data.fields[key]);
      }
      postData.append('file', file);
      xhr.onreadystatechange = () => {
        if(xhr.readyState === 4){
          if(xhr.status === 200 || xhr.status === 204){
            document.getElementById('preview').src = url;
          }
          else{
            //alert('Could not upload file.');
          }
        }
      };
      xhr.send(postData);
	  //deleteTempFile(filename);
    }
    /*
      Function to get the temporary signed request from the Python app.
      If request successful, continue to upload the file using this signed
      request.
    */
    function getSignedRequest(file){
		var email;
		email = document.getElementById('email').value;
		email = email.replace(/@/g , "_");
		email = email.replace(/\./g , "_");
		tempFile = email
		email = email + "_sig.png"
		tempFile = tempFile + Date.now() + "_sig.png"
		const xhr = new XMLHttpRequest();
		const xhrTemp = new XMLHttpRequest();
		xhr.open("GET", "/sign_s3/?file_name="+email+"&file_type="+file.type);
		xhr.onreadystatechange = () => {
        if(xhr.readyState === 4){
          if(xhr.status === 200){
            const response = JSON.parse(xhr.responseText);
            uploadFile(file, response.data, response.url);
          }
          else{
            //alert('Could not get signed URL.');
          }
        }
      };
	  xhrTemp.open("GET", "/sign_s3/?file_name="+tempFile+"&file_type="+file.type);
		xhrTemp.onreadystatechange = () => {
        if(xhrTemp.readyState === 4){
          if(xhr.status === 200){
            const response = JSON.parse(xhrTemp.responseText);
            uploadTempFile(file, response.data, response.url, tempFile);
          }
          else{
            //alert('Could not get signed URL.');
          }
        }
      };
      xhr.send();
	  xhrTemp.send();
    }
    /*
       Function called when file input updated. If there is a file selected, then
       start upload procedure by asking for a signed request from the app.
    */
    function initUpload(){
      const files = document.getElementById('file_input').files;
      const file = files[0];
      if(!file){
        //return alert('No file selected.');
      }
      getSignedRequest(file);
    }
    /*
       Bind listeners when the page loads.
    */
    (() => {
      document.getElementById('file_input').onchange = initUpload;
    })();










// $("button").click(function(e) {
//     e.preventDefault();
//     $.ajax({
//         type: "POST",
//         url: "/pages/test/",
//         data: { 
//             id: $(this).val(), // < note use of 'this' here
//             access_token: $("#access_token").val() 
//         },
//         success: function(result) {
//             alert('ok');
//         },
//         error: function(result) {
//             alert('error');
//         }
//     });
// });

