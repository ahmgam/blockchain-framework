# blockchain protocol

## Authentication

1. authenticator loads registered users id from databases, permissioned users should be pre-registered, every user has unique random string id and mac addresses
2. authenticatior should prodcast that he is active 
3. any other peer revive it's message respond with nounce, random string and timestamp
4. authenticator generates hash with the following {nounce,mac address, secret, timestamp} , generate public and private key and return the result to the other peer
5. if the other peer accepts the connection, it sends response encrtped with public key just sent with it's public key, so both has the public key of each other
