from py2neo import Graph

class Node():
	def __init__(self, m):
		if m.properties['type'] in ['Callee', 'ParameterType', 'IdentifierDeclType']:
			self.type = m.properties['code']
		else:
			self.type = None
		self.child = []	

	def addChild(self, n):
		self.child.append(n)



def getFunctions(cypher):
	FunctionIds = []
	Records = cypher.execute('match(m) where m.type = "FunctionDef" return m.functionId, id(m)')
	for record in Records:
		FunctionIds.append([record[0], record[1]])
	return FunctionIds

def getNodes(cypher, functionId):
	Nodes = {}
	Records = cypher.execute('match(m) where m.functionId = '+str(functionId)+' return m')
	for record in Records:
		m = record.m
		Nodes[m._id] = Node(m)
	return Nodes

def getEdges(cypher, functionId):
	Edges = []
	Records = cypher.execute('match(m)-[r:IS_AST_PARENT]->() where m.functionId = '+str(functionId)+' return r')
	for record in Records:
		r = record.r
		Edges.append([r.start_node._id, r.end_node._id])
	return Edges

def makeTree(Edges, Nodes):
	for edge in Edges:
		Nodes[edge[0]].addChild(edge[1])

def isCantainAPI(treeNodes):		# check if the subtree cantains a API node
	for item in treeNodes:
		if item['type']:
			return True
	return False

def cmpSubTree(newTree, tree):		# check if two trees are the same
	if newTree[0].type != tree[0].type:
		return False
	if len(newTree[0].child) != len(tree[0].child):
		return False
	for i in range(len(newTree[0].child)):
		


def addSubTree(treeNodes, SubTrees):		# if subtree not in SubTrees, add it
	for tree in SubTrees:
		if cmpSubTree(treeNodes, tree) == True:
			return SubTrees.indexof(tree)
		else:
			SubTrees.append(tree)
			return len(SubTrees)-1

def getSubTrees(SubTrees, Nodes, rootId):		# get subtrees of a function, depth is 3
	treeNodes = []			# a list of Node
	root = Nodes[rootId]
	treeNodes.append(root)
	isATree = 0
	if root.child:
		for item in root.child:
			treeNodes.append(Nodes[item])
			if Nodes[item].child:
				for jtem in Nodes[item].child:
					treeNodes.append(Nodes[jtem])
					isATree = 1
	if isATree and isCantainAPI(treeNodes):
		index = addSubTree(treeNodes, SubTrees)		# get the index of the tree or add into list
	if root.child:
		for item in root.child:
			getSubTrees(SubTrees, Nodes, item)

def main():
	graph = Graph()
	cypher = graph.cypher
	FunctionIds = getFunctions(cypher)		# get function id in the whole project
	subTrees = []

	for item in FunctionIds:
		functionId = item[0]
		rootId = item[1]
		Nodes = getNodes(cypher, functionId)	# get all nodes in each function
		Edges = getEdges(cypher, functionId)	# get all ast relations in each function
		makeTree(Edges, Nodes)		# add ast children to nodes, make up an ast tree whose root is Nodes[rootId]
		getSubTrees(SubTrees, Nodes, rootId)


if __name__ == '__main__':
	main()




