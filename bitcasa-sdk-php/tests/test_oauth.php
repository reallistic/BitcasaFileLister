<?php
require_once(dirname(dirname(__FILE__)) . "/BitcasaClient.php");
class TestOAuth extends PHPUnit_Framework_TestCase {
    public function getClient() {
        $client = new BitcasaClient();
        $client->setAccessToken('');
        return $client;
    }
    function testGetInfinitDrive() {
        $client = $this->getClient();
        $drive = $client->getInfiniteDrive();
        $items = $drive->listAll($client);
        $this->assertNotEmpty($items);
    }
}
