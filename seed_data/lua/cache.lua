Cache = {}

function Cache:new()
  local o = { size = 0 }
  setmetatable(o, self)
  self.__index = self
  return o
end

function Cache:add()
  self.size = self.size + 1
end
