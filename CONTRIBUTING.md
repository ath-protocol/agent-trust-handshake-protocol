# Contributing to ATH

Thank you for your interest in contributing to the Agent Trust Handshake Protocol.

## Repository Structure

ATH spans multiple repositories in the [`ath-protocol`](https://github.com/ath-protocol) organization:

| Repository | Description |
|-----------|-------------|
| [agent-trust-handshake-protocol](https://github.com/ath-protocol/agent-trust-handshake-protocol) | Documentation site and specification (this repo) |
| [typescript-sdk](https://github.com/ath-protocol/typescript-sdk) | TypeScript Client SDK |
| [gateway](https://github.com/ath-protocol/gateway) | Reference gateway implementation |

## How to Contribute

### Documentation & Specification

1. Fork this repository
2. Create a feature branch (`git checkout -b my-change`)
3. Make your changes
4. Run the site locally to verify (`npm install && npx mintlify dev`)
5. Submit a pull request

### Protocol Changes

Protocol changes require careful review. Please:

1. Open a [GitHub Discussion](https://github.com/ath-protocol/agent-trust-handshake-protocol/discussions) first to discuss your proposal
2. If the community supports the idea, submit a PR with specification changes
3. Protocol changes must maintain backward compatibility within a major version

### SDK & Gateway

Contribute to the relevant repository under the [ath-protocol](https://github.com/ath-protocol) organization.

### Building a New SDK

See the [SDK page](https://athprotocol.dev/docs/develop/sdk) and the [API Specification](https://athprotocol.dev/specification/0.1/server/registration) for the complete endpoint reference.

## Code of Conduct

See [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md).

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
