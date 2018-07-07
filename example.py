#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jun 30 21:01:11 2018

@author: leosun
"""

from flask import Flask, request
from waitress import serve
from gurobipy import *
import math
import random
import itertools
import os
import logging
from user_agents import parse

app = Flask(__name__)
DEFAULT_N = 20
n = DEFAULT_N

logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    stream_handler = logging.StreamHandler()
    file_handler = logging.FileHandler('RunLog.log')
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)
    logger.setLevel(logging.DEBUG)

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

            result_html = f'''
                n_cities = {n}</br>
                runtime = {runtime:.3f} sec</br>
                Best objective = {objVal:g}</br>
                tour = <code>{' -> '.join(map(str,tour))}</code></br>
                <hr>
                <pre>{mylog}</pre>'''
        else:
            result_html = f'<p>Please enter number of cities!</p>'
    except ValueError as e:
        result_html = f'ValueError: {str(e)}'
    form_html = f'''
        <form method="get">
          <fieldset>
            <legend>User Input:</legend>
            Enter number of cities:
              <input type="range" min="3" max="150" name="n_cities" value="{n}" id="myRange">
              <span id="myValue"></span><br>
              <button type="submit">Submit</button><br>
          </fieldset>
        </form>'''
    form_html += '''
        <script>
            var slider = document.getElementById("myRange");
            var output = document.getElementById("myValue");
            output.innerHTML = slider.value;

            slider.oninput = function() {
              output.innerHTML = this.value;
            }
        </script>'''
    user_agent = str(parse(request.headers.get('User-Agent')))
    real_ip = str(request.headers.get('X-Real-Ip'))
    logger.info(f"""cities {'real_ip':^15} user_agent
                    {n:>6}   {real_ip:^15} {user_agent}
                    """)
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
    m.setParam('Threads',6)

    m.optimize(subtourelim)

    vals = m.getAttr('x', vars)
    selected = tuplelist((i,j) for i,j in vals.keys() if vals[i,j] > 0.5)

    tour = subtour(selected)
    return m.Runtime, m.objVal, tour


if __name__ == '__main__':
#    app.run(debug=True)
    logger.info('================== Begin server ==================')
    serve(app, listen='*:8080')


