<?php
include_once("BitcasaClient.php");
include_once("config.php");

$client_id = OAUTH_CLIENTID;
$secret = OAUTH_SECRET;

if (!isset($_GET['authorization_code']))
{
	header("Location: .");
	die("Authorization code not found");
}

$client = new BitcasaClient();

try {
	if (!$client->authenticate($client_id, $secret)) {
		die("failed to authenticate");
	}
}
catch (Exception $ex) {
	var_dump($ex);
	die($ex->getMessage());
}
if(isset($_GET['depth'])){
	$dpth = $_GET['depth'];
}
else{
	$dpth = 1;
}

header('Location: example.php?depth='.$dpth.'&access_token=' . $client->getAccessToken() ,true, 302);
exit;

?>
