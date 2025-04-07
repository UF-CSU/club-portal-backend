#############################################
## Public Subnets
#############################################

resource "aws_subnet" "public" {
  for_each = toset(local.availability_zones)

  cidr_block              = format("%s.%s.0/24", var.cidr_block_prefix, 1 + index(local.availability_zones, each.key))
  map_public_ip_on_launch = true
  vpc_id                  = aws_vpc.this.id
  availability_zone       = each.value

  tags = merge(
    var.common_tags,
    tomap({
      Name = "${var.prefix}-public-${each.value}",
    }),
    var.public_subnet_tags
  )
}

resource "aws_route_table" "public" {
  for_each = toset(local.availability_zones)

  vpc_id = aws_vpc.this.id

  tags = merge(
    var.common_tags,
    tomap({ Name = "${var.prefix}-public-${each.value}", })
  )
}

resource "aws_route_table_association" "public" {
  for_each = toset(local.availability_zones)

  subnet_id      = aws_subnet.public[each.key].id
  route_table_id = aws_route_table.public[each.key].id
}

resource "aws_route" "public_internet_access" {
  for_each = toset(local.availability_zones)

  route_table_id         = aws_route_table.public[each.key].id
  destination_cidr_block = "0.0.0.0/0" # Access all ip addresses
  gateway_id             = aws_internet_gateway.this.id
}

resource "aws_eip" "public" {
  for_each = toset(local.availability_zones)

  domain = "vpc"

  tags = merge(
    var.common_tags,
    tomap({ Name = "${var.prefix}-public-${each.value}", })
  )
}

resource "aws_nat_gateway" "public" {
  for_each = toset(local.availability_zones)

  allocation_id = aws_eip.public[each.key].id
  subnet_id     = aws_subnet.public[each.key].id

  tags = merge(
    var.common_tags,
    tomap({ Name = "${var.prefix}-public-${each.value}", })
  )
}


#############################################
## Private Subnets
#############################################

resource "aws_subnet" "private" {
  for_each = toset(local.availability_zones)

  cidr_block        = format("%s.%s.0/24", var.cidr_block_prefix, 10 + index(local.availability_zones, each.key))
  vpc_id            = aws_vpc.this.id
  availability_zone = each.value

  tags = merge(
    var.common_tags,
    tomap({
      Name = "${var.prefix}-private-${each.value}",
    }),
    var.private_subnet_tags
  )
}

resource "aws_route_table" "private" {
  for_each = toset(local.availability_zones)

  vpc_id = aws_vpc.this.id

  tags = merge(
    var.common_tags,
    tomap({ Name = "${var.prefix}-private-${each.value}" })
  )
}

resource "aws_route_table_association" "private" {
  for_each = toset(local.availability_zones)

  subnet_id      = aws_subnet.private[each.key].id
  route_table_id = aws_route_table.private[each.key].id
}

resource "aws_route" "private_internet_out" {
  for_each = toset(local.availability_zones)

  route_table_id         = aws_route_table.private[each.key].id
  nat_gateway_id         = aws_nat_gateway.public[each.key].id
  destination_cidr_block = "0.0.0.0/0"
}

