<?php
class UserRepo {
    private array $users = [];
    public function add(string $id): void { $this->users[] = $id; }
}
