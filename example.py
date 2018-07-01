#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jun 30 21:01:11 2018

@author: leosun
"""

from flask import Flask, request
from gurobipy import *
import math
import random
import itertools
import os

app = Flask(__name__)
DEFAULT_N = 20
n = DEFAULT_N

@app.route('/', methods=['GET', 'POST'])
def home():
    global n
    try:
        if 'n_cities' in request.args:
            n = int(request.args.get('n_cities'))
            # Clear log
            with open ("gurobi.log", "w") as myfile:
                myfile.write('')
            runtime, objVal, tour = tsp()
            # Read log
            with open ("gurobi.log", "r") as myfile:
                mylog=''.join(myfile.readlines())

            result_html = f'''n_cities = {n}</br>
                        runtime = {runtime:g} sec</br>
                        Best objective = {objVal:g}</br>
                        tour = <code>{' -> '.join(map(str,tour))}</code></br>
                        <hr>
                        <pre>{mylog}</pre>'''
        else:
            result_html = f'<p>Please enter number of cities!</p>'
    except ValueError as e:
        result_html = f'ValueError: {str(e)}'
    form_html = f'''<form>
          <p>Enter number of cities: <input name="n_cities" value="{n}"></p>
          <p><button type="submit">Submit</button></p>
          </form>'''
    return form_html + result_html


def subtourelim(model, where):
    '''Callback - use lazy constraints to eliminate sub-tours'''
    try:
        if where == GRB.Callback.MIPSOL:
            # make a list of edges selected in the solution
            vals = model.cbGetSolution(model._vars)
            selected = tuplelist((i,j) for i,j in model._vars.keys() if vals[i,j] > 0.5)
            # find the shortest cycle in the selected edge list
            tour = subtour(selected)
            if len(tour) < n:
                # add subtour elimination constraint for every pair of cities in tour
                model.cbLazy(quicksum(model._vars[i,j]
                                      for i,j in itertools.combinations(tour, 2))
                             <= len(tour)-1)
    except KeyboardInterrupt:
        model.terminate()

def subtour(edges):
    '''Given a tuplelist of edges, find the shortest subtour'''
    unvisited = list(range(n))
    cycle = range(n+1) # initial length has 1 more city
    while unvisited: # true if list is non-empty
        thiscycle = []
        neighbors = unvisited
        while neighbors:
            current = neighbors[0]
            thiscycle.append(current)
            unvisited.remove(current)
            neighbors = [j for i,j in edges.select(current,'*') if j in unvisited]
        if len(cycle) > len(thiscycle):
            cycle = thiscycle
    return cycle

def tsp():
    random.seed(1)
    points = [(random.randint(0,100),random.randint(0,100)) for i in range(n)]
    dist = {(i,j) :
        math.sqrt(sum((points[i][k]-points[j][k])**2 for k in range(2)))
        for i in range(n) for j in range(i)}
    m = Model()

    vars = m.addVars(dist.keys(), obj=dist, vtype=GRB.BINARY, name='e')
    for i,j in vars.keys():
        vars[j,i] = vars[i,j] # edge in opposite direction
    m.addConstrs(vars.sum(i,'*') == 2 for i in range(n))

    m._vars = vars
    m.Params.lazyConstraints = 1
#    m.setParam('Threads',6)

    m.optimize(subtourelim)

    vals = m.getAttr('x', vars)
    selected = tuplelist((i,j) for i,j in vals.keys() if vals[i,j] > 0.5)

    tour = subtour(selected)
    return m.Runtime, m.objVal, tour


if __name__ == '__main__':
    app.run()





