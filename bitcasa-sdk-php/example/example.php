<html><head></head><body>
<?php
include_once("../BitcasaClient.php");
include_once("config.php");

$client = new BitcasaClient();
//$client->setAccessToken($_GET["access_token"]);
$client->setAccessTokenFromRequest();


/*
 * EXAMPLE 1 - listing the contents of the Bitcasa Infinite Drive
 */
echo "<h2>Example 1 - list infinite drive</h2>";


try {
	$items = BitcasaInfiniteDrive::listAll($client);
}
catch (Exception $ex) {
	var_dump($ex);
	die("example 1 failed");
}

echo "<table border=1>";
?>
<tr><th>Name</th><th>Type</th><th>Category</th><th>UUID Path</th></tr>
<?
foreach ($items as $key => $item) {
	echo "<tr><td>" . $item->getName()
		. "</td><td>" . $item->getType()
		. "</td><td>" . $item->getCategory()
		. "</td><td>" . $item->getPath() . "</td></tr>";
}

echo "</table>";

/*
 * EXAMPLE 2 - listing the contents of the Bitcasa Mirrors (device list)
 */

echo "<h2>Example 2 - list mirrored folders</h2>";

$items = BitcasaMirrors::listAll($client);

echo "<table border=1>";
?>
<tr><th>Name</th><th>Type</th><th>Category</th><th>Device</th></tr>
<?
foreach ($items as $key => $item) {
	echo "<tr><td>" . $item->getName()
		. "</td><td>" . $item->getType()
		. "</td><td>" . $item->getCategory()
		. "</td><td>" . $item->getOriginDevice() . "</td></tr>";
}

echo "</table>";

/*
 * EXAMPLE 3 - add folder to BitcasaInfinteDrive
 */

echo "<h2>Example 3 - add a folder</h2>";

$bid = $client->getInfiniteDrive();
$item = $bid->add($client, "My New Folder");

echo "<table border=1>";
?>
<tr><th>Name</th><th>Mtime</th><th>type</th><th>Path</th></tr>
<?
echo "<tr><td>" . $item->getName()
. "</td><td>" . $item->getMTime()
. "</td><td>" . $item->getType()
. "</td><td>" . $item->getPath() . "</td></tr>";

echo "</table>";

/*
 * EXAMPLE 4 - rename folder from BitcasaInfinteDrive
 */
echo "<h2>Example 4 rename a folder</h2>";

// get the item from the previous example
$folder = $item;

$item = $folder->rename($client, "NewFolderName");
echo "<table border=1>";
?>
<tr><th>Name</th><th>Mtime</th><th>type</th><th>Path</th></tr>
<?
echo "<tr><td>" . $item->getName()
. "</td><td>" . $item->getMTime()
. "</td><td>" . $item->getType()
. "</td><td>" . $item->getPath() . "</td></tr>";

echo "</table>";

/*
 * EXAMPLE 5 - delete folder from BitcasaInfinteDrive
 */
echo "<h2>Example 5 - delete a folder</h2>";

// still use $folder from the previous example


$item = $folder->remove($client);
echo "<table border=1>";
?>
<tr><th>Name</th><th>Mtime</th><th>type</th><th>Path</th></tr>
<?
echo "<tr><td>" . $item->getName()
. "</td><td>" . $item->getMTime()
. "</td><td>" . $item->getType()
. "</td><td>" . $item->getPath() . "</td></tr>";

echo "</table>";

/*
 * EXAMPLE 6 - upload a file from BitcasaInfinteDrive
 */
echo "<h2>Example 6 - upload a file</h2>";


try {
	$bid = BitcasaInfiniteDrive::getInfiniteDrive($client);
	$result = $bid->upload($client, "/etc/hosts", "UpFile.pdf");
}
catch (Exception $ex) {
	var_dump($ex);
}

echo "<table border=1>";
?>
<tr><th>Name</th><th>Mtime</th><th>type</th><th>Path</th></tr>
<?
echo "<tr><td>" . $result->getName()
. "</td><td>" . $result->getMTime()
. "</td><td>" . $result->getType()
. "</td><td>" . $result->getPath() . "</td></tr>";

echo "</table>";


/*
 * EXAMPLE 7 - copy a file from BitcasaInfinteDrive
 */

echo "<h2>Example 7 - copy a file</h2>";

$file_to_copy = $result;

try {
	$result = $file_to_copy->copy($client, $bid, "hosts.txt");
}
catch (Exception $ex) {
	var_dump($ex);
}

echo "<table border=1>";
?>
<tr><th>Name</th><th>Mtime</th><th>type</th><th>Path</th></tr>
<?
echo "<tr><td>" . $result->getName()
. "</td><td>" . $result->getMTime()
. "</td><td>" . $result->getType()
. "</td><td>" . $result->getPath() . "</td></tr>";

echo "</table>";

/*
 * EXAMPLE 8 - copy a file from BitcasaInfinteDrive
 */

echo "<h2>Example 8 - delete a file</h2>";

$file_to_delete = $file_to_copy;

try {
	$result = $file_to_delete->remove($client);
}
catch (Exception $ex) {
	var_dump($ex);
}

echo "<table border=1>";
?>
<tr><th>Name</th><th>Mtime</th><th>type</th><th>Path</th></tr>
<?
echo "<tr><td>" . $result->getName()
. "</td><td>" . $result->getMTime()
. "</td><td>" . $result->getType()
. "</td><td>" . $result->getPath() . "</td></tr>";

echo "</table>";

?>

</body></html>
