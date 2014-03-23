<?php
/**
 * Bitcasa Client PHP SDK
 * Copyright (C) 2013 Bitcasa, Inc.
 * 215 Castro Street, 2nd Floor
 * Mountain View, CA 94041
 *
 * This file contains an SDK in PHP for accessing the Bitcasa infinite
 * drive.
 *
 * For support, please send email to support@bitcasa.com.
 */

define("BASE_URL", "https://developer.api.bitcasa.com/v1");


/**
 * BitcasaClient
 *
 * This class is used to connect to Bitcasa and perform file system operations
 * It is first required to authenticate or if allready done, set the access token.
 * From there on the application can perform operations.
 */
class BitcasaClient
{
	private $client_id;
	private $secret;
	private $access_token;
	private $base_url;
	private $infinite_drive;
	private $mirrored_folders;


	/**
	 * BitcasaClient constructor - creates an instance of the Bitcasa Client.
	 *
	 * Once an instance of this class is created, either the authenticate() or
	 * the setAccessToken() methods must be called.
	 */
	public function __construct()
	{
		$this->client_id = NULL;
		$this->secret = NULL;
		$this->access_token = NULL;
		$this->base_url = BASE_URL;
		$this->infinite_drive = NULL;
		$this->mirrored_folders = NULL;
	}


	/**
	 * valid - method to determine if this bitcasa client is properly authenticated
	 *
	 * @return true if authenticated, false otherwise
	 */
	public function valid()
	{
		return $this->access_token != NULL;
	}


	/**
	 * setAccessToken - set the access token for this instance
	 *
	 * @param token a string representing the token, assuming that it is valid.
	 * @effects the access token field inside to the instance will be set to the
	 * given paramenter
	 */
	public function setAccessToken($token)
	{
		$this->access_token = $token;
	}


	public static function authorize($client_id, $redirect)
	{
		return BASE_URL . "/oauth2/authenticate?client_id="
			. urlencode($client_id)
			. "&redirect=". $redirect;
	}

	/**
	 * setAccessTokenFromRequest - set the access token if present inside the http
	 *          request
	 * @effects the access token field inside to the instance will be set to the
	 *          given request parameter if present
	 */
	public function setAccessTokenFromRequest()
	{
		if (isset($_REQUEST["access_token"]) && "" != $_REQUEST["access_token"]) {
			$this->access_token = $_REQUEST["access_token"];
		}
		else {
			$this->access_token = NULL;
		}

	}


	/**
	 * accessTokenInput - returns a string to add the access token to the request
	 *
	 * Example: Inside an html form you can place this call:
	 *
	 *     <form method="GET" action="http:/my.uri">
	 *         <?= $client->accessTokenInput() ?>
	 *     </form>
	 *
	 * @return on success, an HTML INPUT element containing the access token as a hidden field.
	 *         On failure, the HTML INPUT element with an unset access token.
	 */
	public function accessTokenInput()
	{
		if ($this->valid()) {
			return '<input type="hidden" name="access_token" value="' . $this->access_token . '"/>';
		}
		else {
			return "";
		}
	}


	/**
	 * getAccessToken - get access token
	 *
	 * @returns the access token if previouly set, NULL otherwise
	 */
	public function getAccessToken()
	{
		return $this->access_token;
	}


	/**
	 * authenticate - authenticate a user gicen the secret and authorization code
	 *
	 * @throws BitcasaException if a Bitcasa Client or server error occurred
	 * @throws HttpException if an HTTP error occurred
	 * @param client_id the application id
	 * @param secret the application secret
	 * @param auth_code the oauth2 authorization code obtained from the redirected call to bitcasa
	 * @return true if the access token was succesfully obtained, false otherwise
	 */
	public function authenticate($client_id, $secret, $auth_code = NULL)
	{
		if ($auth_code == NULL) {
			if (isset($_REQUEST["authorization_code"])) {
				$auth_code = $_REQUEST["authorization_code"];
			}
			else {
				throw new BitcasaException("missing authorization_code");
			}
		}
		$this->client_id = $client_id;
		$this->secret = $secret;
		$this->access_token = NULL;

		$url = "/oauth2/access_token";
		$result = $this->http_get($url, array("secret" => $this->secret,
											  "code" => $auth_code));

		if ($result && isset($result["result"]) && isset($result["result"]["access_token"])) {
			$this->access_token = $result["result"]["access_token"];
			return true;
		}
		else {
			return false;
		}
	}


	/**
	 * createFolder - create a folder inside a given path
	 *
	 * @throws BitcasaException if a Bitcasa Client or server error occurred
	 * @throws HttpException if an HTTP error occurred
	 * @param path full path of parent folder
	 * @param name the name of the new folder
	 * @return The new folder BitcasaItem instance
	 */
	public function createFolder($path, $name)
	{
		$result = $this->http_post("/folders" . $path, array(),
								   $this->encodeArray(array("folder_name" => $name)));
		$result = $this->listResult($result);
		return $result[0];
	}


	/**
	 * uploadStream - upload the contents of a stream to the Bitcasa infinite drive
	 *
	 * @throws BitcasaException if a Bitcasa Client or server error occurred
	 * @throws HttpException if an HTTP error occurred
	 * @param handle the handle to read the contents form
	 * @param path the folder path in which to store the file
	 * @param name the name of the file on the Bitcasa infinite drive
	 * @param exist what to do if the file exists. Default is rename.
	 * @return a BitcasaItem instance containing information on the uploaded file
	 */
	public function uploadStream($handle, $path, $name, $exists="rename")
	{
		$temp = tmpfile();
		$contents = '';

		while (!feof($handle)) {
			$contents .= fread($handle, 8192);
			fwrite($temp, $contents);
		}

		fclose($handle);
		$result = $this->uploadFile($handle, $path, $name, $exists);
		fclose($temp);

		return $result;
	}


	/**
	 * uploadFile - upload a file from the local drive to the Bitcasa infinite drive
	 *
	 * @throws BitcasaException if a Bitcasa Client or server error occurred
	 * @throws HttpException if an HTTP error occurred
	 * @param path the folder path in which to store the file
	 * @param filepath is the path of the file to be uploaded
	 * @param name the name of the file on the Bitcasa infinite drive
	 * @param exist what to do if the file exists. Default is rename.
	 * @return a BitcasaItem instance containing information on the uploaded file
	 */
	public function uploadFile($path, $filepath, $name = NULL, $exists="rename")
	{
		if ($name == NULL) {
			$name = basename($filepath);
		}

		return $this->singleResult($this->http_put_file("/files" . $path,
													  array("exists" => $exists),
													  $name, $filepath));
	}


	/**
	 * downloadStream - download a file from the bitcasa infinite drive into a file stream
	 *
	 * @throws BitcasaException if a Bitcasa Client or server error occurred
	 * @throws HttpException if an HTTP error occurred
	 * @param handle the file handle in which to write the contents of the downloaded file
	 * @param path the location on the Bitcasa infinite drive where the file resides
	 * @return a BitcasaItem instance containing information on the downloaded file
	 */
	public function downloadStream($handle, $path)
	{
		$base = "/files";
		$fields = array();
		$fields["path"] = $path;
		$data = $this->http_get_file($base, $fields);

		if ($data != NULL) {
			fwrite($handle, $data);
			fflush($handle);
		}

		return true;
	}


	/**
	 * downloadFile - download a file from the bitcasa infinite drive into a file stream
	 *
	 * @throws BitcasaException if a Bitcasa Client or server error occurred
	 * @throws HttpException if an HTTP error occurred
	 * @param path the location of the file to be downloaded
	 * @param filepath file path in which to store the downloaded file
	 * @return a BitcasaItem instance containing information on the downloaded file
	 */
	public function downloadFile($path, $filepath)
	{
		$handle = fopen($filepath, "w");
		$response = $client->downloadStream($handle, $this->getPath(), $filepath);
		fclose($handle);

		return $response;
	}


	/**
	 * downoadFileByID - download a file from the Bitcasa infinite drive using the ID
	 * instead of the path. The ID can be obtained from the file's BitcasaItem's
	 * getID() method.
	 *
	 * @throws BitcasaException if a Bitcasa Client or server error occurred
	 * @throws HttpException if an HTTP error occurred
	 * @param handle the file handle in which to write the contents of the downloaded file
	 * @param id of the file to be downloaded (instead of the path)
	 * @return a BitcasaItem instance containing information on the downloaded file
	 */
	public function downoadFileByID($handle, $id)
	{
		$base = "/files/" . $id;

		$fields = array();
		$data = $this->http_get_file($base, $fields);

		if ($data != NULL) {
			fwrite($handle, $data);
			fflush($handle);
		}

		return true;
	}


	/**
	 * listItem - list the contents fo a folder on the Bitcasa Infinite Drive
	 *
	 * @throws BitcasaException if a Bitcasa Client or server error occurred
	 * @throws HttpException if an HTTP error occurred
	 * @param item the folder item
	 * @param category the file category to listed from the infinite drive. Valid categories
	 *        are: photos, video, documents and audio.
	 * @return a list of BitcasaItem instances that are inside the folder. An empty
	 *         array if the folder is empty.
	 */
	public function listItem($item = NULL, $category = NULL)
	{
		if ($item != NULL) {
			// can't list files
			if ($item->isFile()) {
				throw new BitcasaException("Error trying to list a plain file");
			}
			$path = $item->getPath();
		}
		else {
			$bid = $this->getInfiniteDrive();
			$path = $bid->getPath();
		}

		return $this->doListFolder($path, $category);
	}




	/**
	 * removeItem - remove a file or folder from the Bitcasa infinite drive
	 *
	 * @throws BitcasaException if a Bitcasa Client or server error occurred
	 * @throws HttpException if an HTTP error occurred
	 * @param item the BitcasaException representing the file or folder to be removed
	 * @return a BitcasaItem instance containing information on the deleted file or folder
	 */
	public function removeItem($item)
	{
		return $item->remove($this);
	}



	/**
	 * renameItem - rename a given item (file or folder)
	 *
	 * @throws BitcasaException if a Bitcasa Client or server error occurred
	 * @throws HttpException if an HTTP error occurred
	 * @param item a BitcasaItem instance
	 * @param newname the new desired name for the item
	 * @return a BitcasaItem instance representing the modified item
	 */
	public function renameItem($item, $newname)
	{
		return $item->rename($this, $newname);
	}


	/**
	 * copyItem - copy a given item (file or folder)
	 *
	 * @throws BitcasaException if a Bitcasa Client or server error occurred
	 * @throws HttpException if an HTTP error occurred
	 * @param source_item the source item of the bitcasa file or folder to copy
	 * @param target_item the target item of the bitcasa folder in which to copy the source file
	 * @param newname if present the filename of the new file location to be renamed
	 * @param exists action to perform if the target file exists. The default is to overwrite
	 * @return a BitcasaItem instance representing the modified item
	 */
	public function copyItem($source_item, $target_item, $newname = NULL, $exists = "overwrite")
	{
		return $source_item->copy($this, $target_item->getPath(), $newname, $exist);
	}


	/**
	 * moveItem - move a given item (file or folder)
	 *
	 * @throws BitcasaException if a Bitcasa Client or server error occurred
	 * @throws HttpException if an HTTP error occurred
	 * @param source_item the source item of the bitcasa file or folder to move
	 * @param target_item the target item of the bitcasa folder in which to move the source file
	 * @param newname if present the filename of the new file location to be renamed
	 * @param exists action to perform if the target file exists. The default is to overwrite
	 * @return a BitcasaItem instance representing the modified item
	 */
	public function moveItem($source_item, $target_item, $newname = NULL, $exists = "overwrite")
	{
		return $source_item->move($this, $target_item->getPath(), $newname, $exist);
	}


	/**
	 * getInfiniteDrive - The the BitcasaItem representing the Bitcasa Infinite Drive
	 *
	 * @throws BitcasaException if a Bitcasa Client or server error occurred
	 * @throws HttpException if an HTTP error occurred
	 * @return instance of BitcasaInfiniteDrive
	 */
	public function getInfiniteDrive()
	{
		if ($this->infinite_drive == NULL) {
			// will set infinite drive
			$this->doListFolder("/");
		}
		return $this->infinite_drive;
	}


	/*
	 * Private class methods
	 */

	public function doListFolder($path, $category = NULL)
	{
		if ($path == NULL) {
			$path = "/";
		}

		$device = NULL;
		$level = 0;
		$mf = "/Mirrored Folders";

		if ($path == "/") {
			$level = 1;
		}
		else if ($mf == $path) {
			$level = 2;
			$path = "/";
		}
		else if ($this->startsWith($path, $mf . "/")) {
			$device = substr($path, strlen($mf) + 1);
			$level = 3;
			$path = "/";
		}
		$args = array();

		if ($category != NULL) {
			$args["category"] = $category;
			$args["depth"] = 0;
		}
		else {
			$depth = 1;
		}

		$files = $this->http_get("/folders" . $path, $args);
		return $this->listResult($files, $level, $device);
	}


	public function removeFolder($path)
	{
		$result = $this->singleResult($this->http_delete("/folders", array(), $this->encodeArray(array("path" => $path))));
		return $result;
	}


	public function removeFile($path)
	{
		return $this->singleResult($this->http_delete("/files", array(), $this->encodeArray(array("path" => $path))));
	}


	public function copyFolder($oldpath, $newpath, $filename = NULL, $exists = "rename")
	{
		$body = array("operation" => "copy",
					  "from" => $oldpath,
					  "to" => $newpath,
					  "exists" => $exists);

		if ($filename != NULL) {
			$body["filename"] = $filename;
		}

		return $this->singleResult($this->http_post("/folders", array(), $this->encodeArray($body)));
	}


	public function moveFolder($oldpath, $newpath, $filename = NULL, $exists = "rename")
	{
		$body = array("operation" => "move",
					  "from" => $oldpath,
					  "to" => $newpath,
					  "exists" => $exists);
		if ($filename != NULL) {
			$body["filename"] = $filename;
		}
		return $this->singleResult($this->http_post("/folders", array(), $this->encodeArray($body)));
	}


	public function renameFolder($path, $newname, $exists = "rename")
	{
		$body = array("operation" => "rename",
					  "from" => $path,
					  "filename" => $newname,
					  "exists" => $exists);

		return $this->singleResult($this->http_post("/folders", array(), $this->encodeArray($body)));
	}


	public function copyFile($oldpath, $newpath, $filename = NULL, $exists = "overwrite")
	{
		$body = array("operation" => "copy",
					  "from" => $oldpath,
					  "to" => $newpath,
					  "exists" => $exists);

		if ($filename != NULL) {
			$body["filename"] = $filename;
		}

		return $this->singleResult($this->http_post("/files", array(), $this->encodeArray($body)));
	}


	public function moveFile($oldpath, $newpath, $filename = NULL, $exists = "overwrite")
	{
		$body = array("operation" => "move",
					  "from" => $oldpath,
					  "to" => $newpath,
					  "exists" => $exists);

		if ($filename != NULL) {
			$body["filename"] = $filename;
		}

		return $this->singleResult($this->http_post("/files", array(), $this->encodeArray($body)));
	}


	public function renameFile($path, $newname, $exists = "overwrite")
	{
		$body = array("filename" => $newname,
					  "from" => $path,
					  "exists" => $exists);

		return $this->singleResult($this->http_post("/files",
												  array("operation" => "rename"),
												  $this->encodeArray($body)));
	}


	private function startsWith($str, $begin)
	{
		return $begin === "" || strpos($str, $begin) === 0;
	}


	private function listResult($result, $level = 0, $device = NULL) {
		BitcasaException::check($result);
		$mirror = false;

		if (isset($result["error"]) && $result["error"] != NULL) {
			throw new BitcasaException("Error occurred from API call:" . $result["error"]);
		}

		$items = $result["result"]["items"];
		$newres = array();
		$devices = array();

		foreach ($items as $key => $item) {

			$category = $item["category"];
			$name = $item["name"];
			$sync_type = isset($item["sync_type"]) ? $item["sync_type"] : NULL;

			// Infinite drive
			if ($level == 1) {

				if ($category == "folders" && $sync_type == "infinite drive") {
					$this->infinite_drive = $this->makeItem($item);
				}

				// sync folders inside BID
				else if ($category == "folders"
						 && ($sync_type == "backup" || $sync_type == "sync" || $name == "Bitcasa Infinite Drive")) {
					if ($mirror == false) {
						$mirror = true;
						$newres[] = new BitcasaMirrors();
					}
					continue;
				}
				else {
					$newres[] = $this->makeItem($item);
				}
			}

			else if ($level == 2) {

				if ($sync_type == "sync" || $sync_type == "backup") {
					$device = $item["origin_device_id"];

					if (!isset($devices[$device])) {
						$devices[$device] = true;
						$newres[] = new BitcasaDevice($device);
					}
				}
				continue;
			}

			else if ($level == 3) {

				if (($sync_type == "sync" || $sync_type == "backup") && $item["origin_device_id"] == $device) {
					$newres[] = $this->makeItem($item);
				}
				continue;
			}

			else {
				$newres[] = $this->makeItem($item);
			}
		}
		return $newres;
	}


	private function makeResult($result) {
		BitcasaException::check($result);

		if (isset($result["result"])) {
			return $this->makeItem($result["result"]);
		}
		else {
			throw new BitcasaException("missing result");
		}
	}


	private function singleResult($result) {
		BitcasaException::check($result);

		$result = $this->listResult($result);
		if ($result == NULL) {
			throw new BitcasaException("call did not return item information");
		}
		return $result[0];
	}


	private function makeItem($item)
	{
		if (isset($item["category"])) {

			if (strcmp($item["category"], "folders") == 0) {
				if (isset($item["sync_type"])) {

					if (strcmp($item["sync_type"], "infinite drive") == 0) {
						return new BitcasaInfiniteDrive($item);
					}

					else if (strcmp($item["sync_type"], "backup") == 0) {
						return new BitcasaBackupFolder($item);
					}

					else if (strcmp($item["sync_type"], "sync") == 0) {
						return new BitcasaSyncFolder($item);
					}
					else if (strcmp($item["sync_type"], "regular") == 0) {
						return new BitcasaFolder($item);
					}
				}
				else {
					return new BitcasaFolder($item);
				}
			}

			if (strcmp($item["category"], "video") == 0) {
				return new BitcasaVideo($item);
			}

			if (strcmp($item["category"], "music") == 0) {
				return new BitcasaMusic($item);
			}

			if (strcmp($item["category"], "document") == 0) {
				return new BitcasaDocument($item);
			}

			if (strcmp($item["category"], "photo") == 0) {
				return new BitcasaPhoto($item);
			}
		}
		return new BitcasaFile($item);
	}


	private function http_get_file($url, $args = array())
	{
		$full_url = $this->base_url . $url;
		$first = true;

		if ($this->valid()) {
			if ($args == NULL) {
				$args = array();
			}

			$args["access_token"] = $this->access_token;
		}

		if ($args != NULL && count($args) > 0) {

			foreach ($args as $key => $value) {

				if ($first == true) {
					$full_url .= "?";
					$first = false;
				} else {
					$full_url .= "&";
				}

				$full_url .= $key . "=" . $value;
			}
		}

		$r = new HttpRequest($full_url, HttpRequest::METH_GET);

		$r->send();
		$rc = $r->getResponseCode();

		if ($rc >= 200 && $rc < 300) {
			$response = $r->getResponseBody();
			return $response;
		}
		else {
			throw new BitcasaException("Invalid response code", $r->getResponseCode());
		}

		return NULL;
	}


	private function http_get($url, $args = array())
	{
		$full_url = $this->base_url . $url;
		$first = true;

		if ($this->valid()) {
			if ($args == NULL) {
				$args = array();
			}
			$args["access_token"] = $this->access_token;
		}

		if ($args != NULL && count($args) > 0) {

			foreach ($args as $key => $value) {

				if ($first == true) {
					$full_url .= "?";
					$first = false;
				} else {
					$full_url .= "&";
				}

				$full_url .= $key . "=" . $value;
			}
		}

		$r = new HttpRequest($full_url, HttpRequest::METH_GET);

		$r->send();
		$rc = $r->getResponseCode();

		if ($rc >= 200 && $rc < 300) {
			$response = $r->getResponseBody();
			$response = json_decode($response, true);
			BitcasaException::check($response);
			return $response;
		}
		else {
			throw new BitcasaException("Invalid response code", $r->getResponseCode());
		}

		return NULL;
	}


	private function http_delete($url, $args = NULL, $body = NULL)
	{
		$full_url = $this->base_url . $url;
		$first = true;

		if ($this->valid()) {
			if ($args == NULL) {
				$args = array();
			}
			$args["access_token"] = $this->access_token;
		}

		if ($args != NULL && count($args) > 0) {

			foreach ($args as $key => $value) {

				if ($first == true) {
					$full_url .= "?";
					$first = false;
				} else {
					$full_url .= "&";
				}

				$full_url .= $key . "=" . $value;
			}
		}

		$r = new HttpRequest(($full_url), HttpRequest::METH_DELETE);

		if ($body != NULL) {
			$r->setBody($body);
		}

		$r->send();
		$rc = $r->getResponseCode();

		if ($rc >= 200 && $rc < 300) {
			$response = $r->getResponseBody();
			$response = json_decode($response, true);
			BitcasaException::check($response);
			return $response;
		}
		else {
			throw new BitcasaException("Invalid response code", $r->getResponseCode());
		}

		return NULL;
	}


	private function http_post($url, $args = NULL, $body = NULL)
	{
		$full_url = $this->base_url . $url;
		$first = true;

		if ($this->valid()) {

			if ($args == NULL) {
				$args = array();
			}
			$args["access_token"] = $this->access_token;
		}

		if ($args != NULL && count($args) > 0) {

			foreach ($args as $key => $value) {

				if ($first == true) {
					$full_url .= "?";
					$first = false;
				} else {
					$full_url .= "&";
				}

				$full_url .= $key . "=" . $value;
			}
		}

		$r = new HttpRequest($full_url, HttpRequest::METH_POST);

		$r->setBody($body);
		$r->send();
		$rc = $r->getResponseCode();
		if ($rc >= 200 && $rc < 300) {

			$response = $r->getResponseBody();
			$response = json_decode($response, true);
			BitcasaException::check($response);
			return $response;
		}
		else {
			throw new BitcasaException("Invalid response code", $r->getResponseCode());
		}

		return NULL;
	}


	private function http_put_file($url, $args = array(), $filename, $filepath)
	{
		$fields = array("exists" => "rename"); // "file" => $filename
		$full_url = $this->base_url . $url;
		$first = true;

		if ($this->valid()) {

			if ($args == NULL) {
				$args = array();
			}
			$args["access_token"] = $this->access_token;
		}

		$full_url .= $this->encodeArray($args, true);
		$r = new HttpRequest(($full_url), HttpRequest::METH_POST);
		$options = array('connecttimeout' => 300, // timeout on connect 
                        'timeout'  => 300);

		$r->setOptions($options);
		$r->setPostFields($fields);
		$r->addPostFile('file', $filepath);
		$r->send();
		$rc = $r->getResponseCode();

		if ($rc >= 200 && $rc < 300) {
			$response = $r->getResponseBody();
			$response = json_decode($response, true);
			BitcasaException::check($response);
			return $response;
		}
		else {
			throw new BitcasaException("Invalid response code", $r->getResponseCode());
		}

		return NULL;
	}


	private function encodeArray($data, $for_get = false)
	{
		// todo: encode
		if ($data == NULL) {
			$data = array();
		}

		$first = true;
		$result = "";

		foreach ($data as $key => $value) {

			if ($first) {
				if ($for_get) {
					$result .= "?";
				}

				$result .= urlencode($key) . "=" . urlencode($value);
				$first = false;
			}
			else {
				$result .= "&" . urlencode($key) . "=" . urlencode($value);
			}
		}

		return $result;
	}

}


/**
 * BitcasaException class - defines a Bitcasa specific error from either the client or the server
 */
class BitcasaException extends Exception
{

	public static function check($result) {

		if (isset($result["error"]) && $result["error"] != NULL) {

			throw new BitcasaException($result["error"]["message"], $result["error"]["code"]);
		}
		return true;
	}
}



/**
 * BitcasaItem class - the base class for all Bitcasa Folder and File items. This class is
 * abstract and therefore can't be instantiated. Though all subclass of BitcasaItem are
 * public, you should never need to invoke the constructor unless you are doing something
 * really wrong.
 */
abstract class BitcasaItem {

	private $name;
	private $category;
	private $path;
	private $type;
	private $data;

	/**
	 * BitcasaItem constructor. Used by BitcasaClient methods only
	 */
	public function __construct($data = NULL)
	{
		$this->data = $data;

		if ($data != NULL) {
			$this->name = $this->get("name");
			$this->category = $this->get("category");
			$this->path = $this->get("path");
			$this->type = $this->get("type");
		}
	}


	/**
	 * findByName - find a specific BitcasaItem instance that matches the given name
	 *
	 * @param name the name of the file to search
	 * @param data a list of BitcasaItem's returned form a listDir method
	 * @return a BitcasaItem corresponding to the file name or NULL if not found
	 */
	public static function findByName($name, $data) {

		foreach ($data as $key => $value) {

			if (strcmp($name, $value->getName()) == 0) {
				return $value;
			}
		}
		return NULL;
	}


	/**
	 * get - method to get a specifi fields from a BitcasaItem
	 *
	 * @param field the attribute or field from the BitcasaItem
	 * @param defualt in the event the attribute isn't present, return
	 *        a default value. If not present, the default is NULL
	 * @return the attribute value if present, otherwise the
	 *        default value
	 */
	public function get($field, $default = NULL)
	{
		if ($this->data != NULL && $field != NULL) {

			if (isset($this->data[$field])) {
				return $this->data[$field];
			}
		}

		return $default;
    }


	/**
	 * getName - method to get the name of a BitcasaItem
	 *
	 * @return the name of the BitcasaItem if present, NULL otherwise
	 */
	public function getName() {
		return $this->name;
	}


	/**
	 * getCategory - method to get the category of a BitcasaItem
	 *
	 * @return the category of the BitcasaItem if present, NULL otherwise
	 */
	public function getCategory() {
		return $this->category;
	}


	/**
	 * getMirrored - method to get the mirrored attribute of a BitcasaItem. This
	 * attribute is used to determine if the file is mirrored or not
	 *
	 * @return the mirrored attribute of the BitcasaItem if present, NULL otherwise
	 */
	public function getMirrored() {
		return $this->get("mirrored");
	}


	/**
	 * getDeleted -  method to get the deleted attribute of a BitcasaItem. This
	 * attribute is used to determine if the file is deleted or not
	 *
	 * @return the deleted attribute of the BitcasaItem if it's present, NULL otherwise
	 */
	public function getDeleted() {
		return $this->get("deleted");
	}


	/**
	 * getMountPoint - method to get the mount point of a BitcasaItem
	 *
	 * @return the mount point of the BitcasaItem if it's present, NULL otherwise
	 */
	public function getMountPoint() {
		return $this->get("mount_point");
	}


	/**
	 * getType - method to get the type of a BitcasaItem
	 *
	 * @return the type of the BitcasaItem if present, NULL otherwise
	 */
	public function getType() {
		return $this->type;
	}


	/**
	 * getStatus - method to get the status of a BitcasaItem
	 *
	 * @return the status of the BitcasaItem if present, NULL otherwise
	 */
	public function getStatus() {
		return $this->get("status");
	}


	/**
	 * getOriginalDevice - method to get the original device of a BitcasaItem
	 *
	 * @return the original device of the BitcasaItem if present, NULL otherwise
	 */
	public function getOriginDevice() {
		return $this->get("origin_device_id");
	}


	/**
	 * getName - method to get the Modification time of a BitcasaItem
	 *
	 * @return the modification of the BitcasaItem if present, NULL otherwise
	 */
	public function getMtime() {
		return $this->get("mtime");
	}


	/**
	 * getSize - method to get the size of a BitcasaItem
	 *
	 * @return the size of the BitcasaItem if present, NULL otherwise
	 */
	public function getSize() {
		return $this->get("size");
	}


	/**
	 * getAlbum - method to get the album of a BitcasaItem
	 *
	 * @return the album of the BitcasaItem if present, NULL otherwise
	 */
	public function getAlbum() {
		return $this->get("album");
	}


	/**
	 * getID - method to get the ID of a BitcasaItem
	 *
	 * @return the ID of the BitcasaItem if present, NULL otherwise
	 */
	public function getID() {
		return $this->get("id");
	}


	/**
	 * getManifestName - method to get the manifest name of a BitcasaItem
	 *
	 * @return the manifestname of the BitcasaItem if present, NULL otherwise
	 */
	public function getManifestName() {
		return $this->get("manifest_name");
	}


	/**
	 * getExtension - method to get the extension of a BitcasaItem
	 *
	 * @return the extension of the BitcasaItem if present, NULL otherwise
	 */
	public function getExtension() {
		return $this->get("extension");
	}


	/**
	 * getDuplicates - method to get the duplicates of a BitcasaItem
	 *
	 * @return the duplicates of the BitcasaItem if present, NULL otherwise
	 */
	public function getDuplicates() {
		return $this->get("duplicates");
	}


	/**
	 * getIncomplete - method to get the incomplete status (for file upload) of a BitcasaItem
	 *
	 * @return the incomplete status of the BitcasaItem if present, NULL otherwise
	 */
	public function getIncomplete() {
		return $this->get("incomplete");
	}


	/**
	 * getPath - method to get the path of a BitcasaItem
	 *
	 * @return the path of the BitcasaItem if present, NULL otherwise
	 */
	public function getPath() {
		return $this->path;
	}


	/**
	 * getSyncType - method to get the sync type of a BitcasaItem
	 *
	 * @return the sync type of the BitcasaItem if present, NULL otherwise
	 */
	public function getSyncType() {
		return $this->get("sync_type");
	}


	/**
	 * isFolder - check whether a BitcasaItem is a folder
	 *
	 * @return true if the BitcasaItem is a folder, false otherwise
	 */
	public function isFolder() {
		return strcmp("folders", $this->category) == 0 ? true : false;
	}


	/**
	 * isFile - check whether a BitcasaItem is a file
	 *
	 * @return true if the BitcasaItem is a file, false otherwise
	 */
	public function isFile() {
		return !$this->isFolder();
	}


	/**
	 * getInfiniteDrive - get an instance of the Bitcasa Infinite Drive
	 *
	 * @throws BitcasaException if a Bitcasa Client or server error occurred
	 * @throws HttpException if an HTTP error occurred
	 * @param An authenticated BitcasaClient instance
	 * @return a BitcasaInfiniteDrive instance
	 */
	public static function getInfiniteDrive($client) {
		return $client->getInfiniteDrive();
	}

	/**
	 * remove - delete a file or folder from the Bitcasa Infinite Drive
	 *
	 * @throws BitcasaException if a Bitcasa Client or server error occurred
	 * @throws HttpException if an HTTP error occurred
	 *
	 * @param client An authenticated BitcasaClient instance
	 * @return a BitcasaItem instance representing the item removed on the 
	 * infinite drive.
	 */
	abstract public function remove($client);

	/**
	 * move - move a file or folder on the Bitcasa Infinite Drive
	 *
	 * @throws BitcasaException if a Bitcasa Client or server error occurred
	 * @throws HttpException if an HTTP error occurred
	 *
	 * @param client An authenticated BitcasaClient instance
	 * @param item instance of the BitcasaItem to be moved
	 * @param newname if present, the new name for the moved file or folder
	 * @return a BitcasaItem instance representing the item moved on the 
	 * infinite drive.
	 */
	abstract public function move($client, $item, $newname = NULL);

	/**
	 * copy - copy a file or folder on the Bitcasa Infinite Drive
	 *
	 * @throws BitcasaException if a Bitcasa Client or server error occurred
	 * @throws HttpException if an HTTP error occurred
	 *
	 * @param client An authenticated BitcasaClient instance
	 * @param item instance of the BitcasaItem to be copied
	 * @param newname if present, the new name for the copied file or folder
	 * @return a BitcasaItem instance representing the item copied on the 
	 * infinite drive.
	 */
	abstract public function copy($client, $item, $newname = NULL);

	/**
	 * rename - rename a file or folder on the Bitcasa Infinite Drive
	 *
	 * @throws BitcasaException if a Bitcasa Client or server error occurred
	 * @throws HttpException if an HTTP error occurred
	 *
	 * @param client An authenticated BitcasaClient instance
	 * @param item instance of the BitcasaItem to be renamed
	 * @return a BitcasaItem instance representing the item renamed on the 
	 * infinite drive.
	 */
	abstract public function rename($client, $name);


	/**
	 * isVideo - check whether a BitcasaItem is a video file
	 *
	 * @return true if the BitcasaItem is a video file, false otherwise
	 */
	public function isVideo() {
		return false;
	}


	/**
	 * isDocument - check whether a BitcasaItem is a document file
	 *
	 * @return true if the BitcasaItem is a document file, false otherwise
	 */
	public function isDocument() {
		return false;
	}


	/**
	 * isMusic - check whether a BitcasaItem is a music file
	 *
	 * @return true if the BitcasaItem is a music file, false otherwise
	 */
	public function isMusic() {
		return false;
	}


	/**
	 * isPhoto - check whether a BitcasaItem is a photo or image file
	 *
	 * @return true if the BitcasaItem is a photo or image file, false otherwise
	 */
	public function isPhoto() {
		return false;
	}


	/**
	 * isMirrors - check whether a BitcasaItem is a mirrored folder
	 *
	 * @return true if the BitcasaItem is a mirrored folder, false otherwise
	 */
	public function isMirrors() {
		return false;
	}


	/**
	 * isDevice - check whether a BitcasaItem is a device folder
	 *
	 * @return true if the BitcasaItem is a device folder, false otherwise
	 */
	public function isDevice() {
		return false;
	}


	/**
	 * isBackup - check whether a BitcasaItem is a backup folder
	 *
	 * @return true if the BitcasaItem is a backup folder, false otherwise
	 */
	public function isBackup() {
		return false;
	}


	/**
	 * isSync - check whether a BitcasaItem is a sync folder
	 *
	 * @return true if the BitcasaItem is a sync folder, false otherwise
	 */
	public function isSync() {
		return false;
	}


	/**
	 * isReadOnly - check whether a BitcasaItem is a read only folder
	 *
	 * @return true if the BitcasaItem is a read only folder, false otherwise
	 */
	public function isReadOnly()
	{
		return false;
	}

	/**
	 * isInfiniteDrive - check whether a BitcasaItem is the Bitcasa infinite drive
	 *
	 * @return true if the BitcasaItem is the infinite drive, false otherwise
	 */
	public function isInfiniteDrive() {
		return false;
	}

}


/**
 * BitcasaFile class - base class for all the different file type items on the Bitcasa infinite drive
 */
class BitcasaFile extends BitcasaItem {

	public function remove($client) {
		return $client->removeFile($this->getPath());
	}


	public function rename($client, $name) {
		return $client->renameFile($this->getPath(), $name);
	}


	public function move($client, $item, $newname = NULL) {
		if (!is_string($item)) {

			if (!is_subclass_of($item, "BitcasaFolder")) {
				throw new BitcasaException("Invalid Paramenter");
			}

			$item = $item->getPath();
		}

		return $client->moveFolder($this->getPath(), $item, $newname);
	}


	public function copy($client, $item, $newname = NULL) {
		if (!is_string($item)) {

			if (!is_subclass_of($item, "BitcasaFolder")) {
				throw new BitcasaException("Invalid Paramenter");
			}

			$item = $item->getPath();
		}

		return $client->copyFile($this->getPath(), $item, $newname);
	}


	/**
	 * download - method user to don load an file from the infinite drive
	 *
	 * @throws BitcasaException if a Bitcasa Client or server error occurred
	 * @throws HttpException if an HTTP error occurred
	 * @param client An authenticated BitcasaClient instance
	 * @param filepath the path in which to store the downloaded file
	 * @return a BitcasaItem instance containing information on the file downloaded.
	 */
	public function download($client, $filepath) {
		$handle = fopen($filepath, "w");
		$response = $client->downloadStrean($handle, $this->getPath(), $filepath);
		fclose($handle);

		return $response;
	}
}


/**
 * BitcasaFolder class - class representing a folder item on the Bitcasa Infinite drive
 */
class BitcasaFolder extends BitcasaItem {

	/**
	 * dir - list the contents of this folder instance
	 *
	 * @throws BitcasaException if a Bitcasa Client or server error occurred
	 * @throws HttpException if an HTTP error occurred
	 * @param client a BitcasaClient instance that is authenticated
	 * @return Upon success, an array of BitcasaItem instances representing
	 *         the contents of this BitcasaFolder item. Upon failure and
	 *         exception will be returned, or NULL in the event the folder
	 *         is empty.
	 */
	public static function listDir($client) {
		return $client->doListFolder($this->getPath());
	}


	public function remove($client) {
		return $client->removeFolder($this->getPath());
	}


	public function add($client, $name) {
		return $client->createFolder($this->getPath(), $name);
	}


	public function rename($client, $name) {
		return $client->renameFolder($this->getPath(), $name);
	}


	public function move($client, $item, $newname = NULL) {
		if (!is_string($item)) {

			if (!is_subclass_of($item, "BitcasaFolder")) {
				throw new BitcasaException("Invalid Paramenter");
			}

			$item = $item->getPath();
		}

		return $client->moveFolder($this->getPath(), $item, $newname);
	}


	public function copy($client, $item, $newname = NULL)
	{
		if (!is_string($item)) {

			if (!is_subclass_of($item, "BitcasaFolder")) {
				throw new BitcasaException("Invalid Paramenter");
			}

			$item = $item->getPath();
		}

		return $client->copyFolder($this->getPath(), $item, $newnme);
	}


	/**
	 *
	 * @throws BitcasaException if a Bitcasa Client or server error occurred
	 * @throws HttpException if an HTTP error occurred
	 */
	public function upload($client, $filepath, $name = NULL)
	{
		return $client->uploadFile($this->getPath(), $filepath, $name);
	}
}


/**
 * BitcasaReadOnlyFolder class - base class for all the Bitcasa foder type items
 * that are read-only.
 */
class BitcasaReadOnlyFolder extends BitcasaFolder
{

	public function isReadOnly()
	{
		return true;
	}

	public function add($client, $name)
	{
		throw new BitcasaException("Can't add subfolders to this folder");
	}

	public function remove($client)
	{
		throw new BitcasaException("Can't delete this folder");
	}

	public function rename($client, $name)
	{
		throw new BitcasaException("Can't rename this folder");
	}

	public function move($client, $item, $newname = NULL)
	{
		throw new BitcasaException("Can't move this folder");
	}

	public function copy($client, $item, $newname = NULL)
	{
		throw new BitcasaException("Can't copy from this folder");
	}

	public function upload($client, $filepath, $name = NULL)
	{
		throw new BitcasaException("Can't upload files into this folder");
	}
}


/**
 * BitcasaPhoto class - An instance of this class represents a file that has been
 * identified on the Bitcasa Infinite drive as a photo or an image.
 */
class BitcasaPhoto extends BitcasaFile
{

	public function isPhoto()
	{
		return true;
	}
}


/**
 * BitcasaVideo class - An instance of this class represents a file that has been
 * identified on the Bitcasa Infinite drive as a video or movie.
 */
class BitcasaVideo extends BitcasaFile {

	public function isVideo()
	{
		return true;
	}
}


/**
 * BitcasaDocument class - An instance of this class represents a file that has been
 * identified on the Bitcasa Infinite drive as a document.
 */
class BitcasaDocument extends BitcasaFile {

	public function isDocument()
	{
		return true;
	}
}


/**
 * BitcasaMusic class - An instance of this class represents a file that has been
 * identified on the Bitcasa Infinite drive as a music or an audio file.
 */
class BitcasaMusic extends BitcasaFile {

	public function isMusic()
	{
		return true;
	}
}


/**
 * BitcasaMirrors class - An instance of this class represents Mirrors folder
 * for given devices on the Bitcasa Infinite drive.
 */
class BitcasaMirrors extends BitcasaReadOnlyFolder
{

	/**
	 *
	 */
	public function __construct()
	{
		parent::__construct(array("type" => 1,
								  "name" => "Mirrored Folders",
								  "category" => "folders",
								  "path" => "/Mirrored Folders"));
	}


	public static function listAll($client) {
		return $client->doListFolder("/Mirrored Folders");
	}


	public function isMirrors() {
		return true;
	}

}


/**
 * BitcasaDevice class - An instance of this class represents a mirrored folder
 * for a given device on the Bitcasa Infinite drive.
 */
class BitcasaDevice extends BitcasaReadOnlyFolder
{

	/**
	 *
	 */
	public function __construct($device)
	{
		parent::__construct(array("type" => 1,
								  "name" => $device,
								  "category" => "folders",
								  "path" => "/Mirrored Folders/" . $device));
	}


	public function isDevice() {
		return true;
	}

}


/**
 * BitcasaSyncFolder class - An instance of this class represents sync folder
 * on the Bitcasa Infinite drive.
 */
class BitcasaSyncFolder extends BitcasaReadOnlyFolder
{

	public function isSync() {
		return true;
	}

}


/**
 * BitcasaBackupFolder class - An instance of this class represents backup folder
 * on the Bitcasa Infinite drive.
 */
class BitcasaBackupFolder extends BitcasaReadOnlyFolder
{

	public function isBackup() {
		return true;
	}
}


/**
 * BitcasaInfiniteDrive class - An instance of this class represents a 
 * the Bitcasa Infinite drive.
 */
class BitcasaInfiniteDrive extends BitcasaFolder
{

	public function isInfiniteDrive() {
		return true;
	}

	public static function listAll($client) {
		return $client->listItem();
	}

	public function remove($client)
	{
		throw new BitcasaException("Can't delete this folder");
	}

	public function rename($client, $name)
	{
		throw new BitcasaException("Can't rename this folder");
	}

	public function move($client, $item, $newname = NULL)
	{
		throw new BitcasaException("Can't move this folder");
	}

	public function copy($client, $item, $newname = NULL)
	{
		throw new BitcasaException("Can't copy from this folder");
	}

}

?>
