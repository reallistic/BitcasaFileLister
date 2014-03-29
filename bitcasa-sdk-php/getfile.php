<?php

if(isset($_GET['path']) && isset($_GET['access_token'])){
	
    include_once("BitcasaUtils.php");
    $at=$_GET["access_token"];
    $path=$_GET['path'];
    $name=$_GET['name'];
    $fileinfo = json_decode(basicCurlGet("https://developer.api.bitcasa.com/v1/files/$path?access_token=$at"));
    $fileinfo = $fileinfo->result;
    /*echo "<pre>";
    	print_r($fileinfo);
    echo "</pre>";*/
	header('Content-Description: File Transfer');
	header('Content-Type: application/octet-stream');
	header('Content-Disposition: attachment; filename="'.$name.'"'); //<<< Note the " " surrounding the file name
	header('Content-Transfer-Encoding: binary');
	header('Connection: Keep-Alive');
	header('Expires: 0');
	header('Cache-Control: must-revalidate, post-check=0, pre-check=0');
	header('Pragma: public');
	header('Content-Length: ' . $fileinfo->size);
    $inc=1024*1024*5;
    $pos=0;
    while($pos< $fileinfo->size){
		if($pos+$inc >$fileinfo->size){
			$inc = $fileinfo->size-$pos+1;
		}
		$pos+=$inc;
		$file = basicCurlGet("https://developer.api.bitcasa.com/v1/files/$name?access_token=$at&path=$path", array("Range: bytes=$pos-".($pos+($inc-1))));
		echo $file;
	}
	
	//echo $fileinfo->size;
}
else{
	header("Location: /bitcasafilelister");
}
exit;