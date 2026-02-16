pragma solidity ^0.8.0;

contract Vault {
    uint256 public balance;
    function deposit(uint256 amount) public { balance += amount; }
}
