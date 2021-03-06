from py2neo import Graph
import numpy as np
import copy
import sys
import math

np.set_printoptions(threshold='nan')

class Node():
	def __init__(self, m):
		if m.properties['type'] in ['Callee', 'ParameterType', 'IdentifierDeclType']:
			self.type = m.properties['code']
			if '[' in self.type:
				self.type = self.type.split('[')[0]+'array'
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
		Nodes[edge[0]].addChild(edge[1])		# the nodes in the child list is ordered by	fixed order

def isCantainAPI(treeNodes):		# check if the subtree cantains a API node
	for item in treeNodes:
		if item.type:
			return True
	return False

def cmpSubTree(newTree, tree):		# check if two trees are the same
	for i in range(len(newTree)):
		if newTree[i].type != tree[i].type or len(newTree[i].child) != len(tree[i].child):
			return False
	return True


def addSubTree(treeNodes, SubTrees):		# if subtree not in SubTrees, add it, else return index
	for tree in SubTrees:
		if cmpSubTree(treeNodes, tree) == True:
			return SubTrees.index(tree)
	SubTrees.append(treeNodes)
	return len(SubTrees)-1

def getSubTrees(SubTrees, Nodes, rootId, treeSequence):		# get subtrees of a function, depth is 3
	treeNodes = []			# a list of Node
	root = Nodes[rootId]
	treeNodes.append(root)
	isATree = 0
	if root.child:
		for item in root.child:
			treeNodes.append(Nodes[item])
			if Nodes[item].child:
				for jtem in Nodes[item].child:
					treeNodes.append(copy.copy(Nodes[jtem]))
					treeNodes[-1].child = []		# set the 3rd layer nodes child to null
					isATree = 1
	if isATree and isCantainAPI(treeNodes):
		index = addSubTree(treeNodes, SubTrees)		# get the index of the tree or add into list
		treeSequence.append(index)
	if root.child:
		for item in root.child:
			getSubTrees(SubTrees, Nodes, item, treeSequence)

def makeMat(Matrix):
	def is_greater_than_zero(array):
		return len(array) > 0

	itemLength = np.max(map(np.max, filter(is_greater_than_zero, Matrix)))+1		# np.max return the largest index of the subStree, which is length-1
	NewMat = np.zeros((len(Matrix), itemLength))
	for i in range(len(Matrix)):
		for j in range(len(Matrix[i])):
			NewMat[i][Matrix[i][j]] += 1
	return NewMat			# in the formmat of np.array, not matrix, for tfIdf

def tfIdf(Matrix):
	d = len(Matrix)			# D
	idf = np.zeros(np.shape(Matrix)[1])
	for i in range(np.shape(Matrix)[1]):
		line = Matrix[:,i]
		idf[i] = math.log(10, sum(np.greater(line, 0))*1.0/d)
	tf = copy.copy(Matrix)
	for i in range(len(tf)):		# tf
		line_sum = sum(tf[i])
		for j in range(len(tf[i])):
			if line_sum == 0:
				tf[i][j] = 0
			else:
				tf[i][j] = tf[i][j]*1.0 / line_sum
	for i in range(np.shape(tf)[1]):
		tf[:,i] = tf[:,i]*idf[i]
	return np.mat(tf).T		# tfidf and transpose

def findFunctionIndex(toCheck, FunctionIds):
	for item in FunctionIds:
		if item[0] == toCheck:
			return FunctionIds.index(item)
	return -1


def calSimilarity(Vt, toCheck, functionNum):
	simList = []
	line2Check = Vt[:60, toCheck]
	norm = np.linalg.norm(line2Check)
	for i in range(functionNum):
		line = Vt[:60, i]
		sim = np.vdot(line, line2Check) / (np.linalg.norm(line)*norm)		# calculate the cosine similarity
		simList.append(abs(sim))
	return simList

def printSubTree(subtree):
	print 'this subtree is:'
	for node in subtree:
		print 'type:'
		print node.type
		print 'length:'
		print len(node.child)

def main():
	matrixPath = sys.argv[2]
	graph = Graph()
	cypher = graph.cypher
	FunctionIds = getFunctions(cypher)		# get function id in the whole project
	functionNum = len(FunctionIds)
	SubTrees = []
	Map = []
	Matrix = []

	if sys.argv[1] == 'load':
		Matrix = np.load(matrixPath)
		U, Sigma, Vt = np.linalg.svd(Matrix)		# SVD with numpy
		toCheck = findFunctionIndex(int(input('input one integer:\n')), FunctionIds)	# input function id to check
		if toCheck == -1:
			raise IndexError("Function id not match.")
		simList = calSimilarity(Vt, toCheck, functionNum)		# calculate and sort the cosine similarities of Vt's cols (i.e. V's rows)
		indexList = np.argsort(-np.array(simList))			# sort by similarity
		for num in indexList[:20]:
			print FunctionIds[num][0]
			print simList[num]
		return		

	for item in FunctionIds:
		functionId = item[0]
		rootId = item[1]
		Nodes = getNodes(cypher, functionId)	# get all nodes in each function
		Edges = getEdges(cypher, functionId)	# get all ast relations in each function
		makeTree(Edges, Nodes)		# add ast children to nodes, make up an ast tree whose root is Nodes[rootId]
		treeSequence = []
		getSubTrees(SubTrees, Nodes, rootId, treeSequence)
		treeSequence = np.array(treeSequence)
		Matrix.append(treeSequence)
		print 'processing function {0}/{1}...'.format(FunctionIds.index(item), functionNum)

	Matrix = makeMat(Matrix)		# change the sequences into a matrix
	weights = tfIdf(Matrix)
	Matrix = np.multiply(np.mat(Matrix).T, weights)
	np.save(matrixPath, Matrix)


if __name__ == '__main__':
	main()