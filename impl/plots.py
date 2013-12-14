import matplotlib.pyplot as plt

def barplot(bardata, errors=None, xlabels=None, colors=('#000099', '#009900'), ecolor='#aa0000'):
    import numpy as np
    
    if xlabels is not None:
        ind = np.arange(len(xlabels))
    else:
        ind = len(bardata[0])
    
    width = 0.35
    
    fig, ax = plt.subplots()
    series = []
    yerr = None
    for i in xrange(len(bardata)):
        if errors is not None:
            yerr = errors[i]
        bar = ax.bar(ind + width * i + width / 2, bardata[i], width, color=colors[i], yerr=yerr, ecolor=ecolor)
        series.append(bar)
    
    ax.set_ylabel('Average rating for movie')
    ax.set_ylim((1, 5))
    ax.set_title('Average ratings from Twitter and Netflix data')
    ax.set_xticks(ind + width * (len(bardata) - 1) + width / 2)
    if xlabels is not None:
        ax.set_xticklabels(xlabels)
    
    ax.legend(map(lambda rects: rects[0], series), ('Twitter', 'Netflix'))
    
    return plt

def lineplot(predictions, ratings, titles):
    import numpy as np
    
    xs = range(1, len(titles) + 1)
    
    fig, ax = plt.subplots()
    
    ax.set_ylim((1, 5.5))
    
    ax.plot(xs, predictions, 'g', label=u"Predictions")
    ax.plot(xs, ratings, 'b--', label=u"Benchmark")
    
    ax.set_xticklabels(titles)
    ax.legend()
    
    return plt
