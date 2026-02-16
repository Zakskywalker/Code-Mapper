class Account
  def initialize(id)
    @id = id
  end

  def label
    "acct-#{@id}"
  end
end
