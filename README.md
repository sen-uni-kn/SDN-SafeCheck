*SDN-SafeCheck* is a tool for automatically identifying all the undesired behaviours that lead to the violation of safety properties within software defined networks (SDNs) expressible in the NetKAT network programming language. In our setting, a safe behaviour is characterised by a NetKAT policy which does not enable forwarding packets from an ingress *in* to an undesirable egress *out*. The tool automatically identifies all undesired behaviours leading to *out*, whenever provided with a NetKAT program describing the end-to-end behaviour of the network, when starting from *in*. *SDN−SafeCheck* is based on Maude equational theories and the devised equational system is Church-Rosser and terminating, thus it evaluates to a unique result explaining safety violations in a given NetKAT program.


#### Requirements

Maude 2.7.1., which can be obtained from:
http://maude.cs.illinois.edu/w/index.php/All_Maude_2_versions#Maude_2.7.1

python3.5 or higher

#### Usage

You may either set the MAUDE_LIB environment variable or give the path where the maude executable is located with the option '-m'.
The user is also given the option to specify a timeout duration with option '-t'.

	python netkat_eq.py input_file [-m path_to_maude] [-t timeout]


#### Input format

.json file containing the keys:

- fields: Predefined fields, with their name, type and range. Only integer and category types are supported.
- in: Ingress point. 
- out: Undesirable egress.
- unfold: The number of unfoldings.
- policy: Routing policy.
- topology: Network topology.

An example input file may be found in example.json.

