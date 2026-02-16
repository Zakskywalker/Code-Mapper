pub struct User {
    pub id: String,
    pub name: String,
}

impl User {
    pub fn new(id: &str, name: &str) -> Self {
        Self { id: id.into(), name: name.into() }
    }

    pub fn display(&self) -> String {
        format!("{} ({})", self.name, self.id)
    }
}
