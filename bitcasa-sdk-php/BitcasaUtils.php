<?php

function recurseFolders($item,$client){
	if($item->getType() == 1){
		$items = $item->listDir($client);
		foreach ($items as $key => $item) {
			echo "<tr><td>" . $item->getName()
				. "</td><td>" . $item->getType()
				. "</td><td>" . $item->getCategory()
				. "</td><td>" . $item->getPath() . "</td></tr>";
			if($item->getType() == 1){
				//recurseFolders($item,$client);
			}
		}
	}
}

function basicCurlGet($url){
	$ch = curl_init(); 
    // set url 
    curl_setopt($ch, CURLOPT_URL, $url); 

    //return the transfer as a string 
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, 1); 

    // $output contains the output string 
    $output = curl_exec($ch); 

    // close curl resource to free up system resources 
    curl_close($ch);
    return $output;
}

function basicCurlPost($url, $data){
	$ch = curl_init(); 
    // set url
   	foreach($data as $key=>$value) { $fields_string .= $key.'='.$value.'&'; }
	rtrim($fields_string, '&');

    curl_setopt($ch,CURLOPT_URL, $url);
	curl_setopt($ch,CURLOPT_POST, count($data));
	curl_setopt($ch,CURLOPT_POSTFIELDS, $fields_string);

    // $output contains the output string 
    $output = curl_exec($ch); 

    // close curl resource to free up system resources 
    curl_close($ch);
    return $output;
}

?>