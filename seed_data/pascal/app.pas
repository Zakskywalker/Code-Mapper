program Seed;

type
  TApp = class
    Name: string;
    function Run: string;
  end;

function TApp.Run: string;
begin
  Result := 'ok';
end;
