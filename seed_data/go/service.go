package seed

type Service struct {
    Name string
}

func NewService(name string) Service {
    return Service{Name: name}
}

func (s Service) Hello() string {
    return "hello " + s.Name
}
