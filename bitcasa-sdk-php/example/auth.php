<?php
include_once("../BitcasaClient.php");
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


header('Location: example.php?access_token=' . $client->getAccessToken() ,true, 302);
exit;

?>
